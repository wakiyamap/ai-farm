"""Run 8980b787: Elysium v3-style pool census from recent Swap logs (topic-only), then token pairs that trade on
two or more pools and their mid gap versus fees. Research lane, 0 fork, 0 tx.
usage: r8980-pairs.py <blocks> <page>"""
import collections, json, os, sys, urllib.request
RELAY = os.environ["RPC_RELAY_URL"].rstrip("/") + "/elysium?lane=research"
SWAP = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"  # cast keccak Swap(address,address,int256,int256,uint160,uint128,int24)
total, page = int(sys.argv[1]), int(sys.argv[2])

def post(body):
    req = urllib.request.Request(RELAY, json.dumps(body).encode(), {"content-type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def rpc(m, p):
    a = post({"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
    if "error" in a:
        raise RuntimeError(str(a["error"])[:200])
    return a["result"]

head = int(rpc("eth_blockNumber", []), 16) - 5
cnt = collections.Counter()
b, pages = head - total, 0
while b < head:
    e = min(head, b + page - 1)
    logs = rpc("eth_getLogs", [{"fromBlock": hex(b), "toBlock": hex(e), "topics": [SWAP]}])
    pages += 1
    for l in logs:
        cnt[l["address"]] += 1
    b = e + 1
print("head", head, "blocks", total, "pages", pages, "swap logs", sum(cnt.values()), "pools", len(cnt))
pools = list(cnt)
SEL = {"token0": "0x0dfe1681", "token1": "0xd21220a7", "slot0": "0x3850c7bd", "fee": "0xddca3f43", "liq": "0x1a686502", "factory": "0xc45a0155"}
info = {}
for i in range(0, len(pools), 3):
    chunk = pools[i:i + 3]
    calls, idx = [], []
    for p in chunk:
        for k, s in SEL.items():
            calls.append({"jsonrpc": "2.0", "id": len(calls), "method": "eth_call", "params": [{"to": p, "data": s}, "latest"]})
            idx.append((p, k))
    for x in post(calls):
        p, k = idx[x["id"]]
        info.setdefault(p, {})[k] = x.get("result")
toks = set()
for p, d in info.items():
    for k in ("token0", "token1"):
        if d.get(k) and len(d[k]) == 66:
            d[k] = "0x" + d[k][26:]
            toks.add(d[k])
        else:
            d[k] = None
toks = list(toks)
meta = {}
for i in range(0, len(toks), 8):
    chunk = toks[i:i + 8]
    calls, idx = [], []
    for t in chunk:
        for k, s in (("sym", "0x95d89b41"), ("dec", "0x313ce567")):
            calls.append({"jsonrpc": "2.0", "id": len(calls), "method": "eth_call", "params": [{"to": t, "data": s}, "latest"]})
            idx.append((t, k))
    for x in post(calls):
        t, k = idx[x["id"]]
        meta.setdefault(t, {})[k] = x.get("result")

def sym(t):
    r = meta.get(t, {}).get("sym")
    try:
        raw = bytes.fromhex(r[2:])
        n = int.from_bytes(raw[32:64], "big")
        return raw[64:64 + n].decode("ascii", "replace")[:12]
    except Exception:
        return t[:8]

def dec(t):
    try:
        return int(meta[t]["dec"], 16)
    except Exception:
        return 18

pairs = collections.defaultdict(list)
for p, d in info.items():
    if not d.get("token0") or not d.get("token1") or not d.get("slot0") or len(d["slot0"]) < 66:
        continue
    s = int(d["slot0"][2:66], 16)
    if s == 0:
        continue
    px = (s / 2**96) ** 2 * 10 ** (dec(d["token0"]) - dec(d["token1"]))  # token1 per token0, human
    fee = int(d["fee"], 16) if d.get("fee") and len(d["fee"]) == 66 else None
    liq = int(d["liq"], 16) if d.get("liq") and len(d["liq"]) == 66 else None
    fac = "0x" + d["factory"][26:] if d.get("factory") and len(d["factory"]) == 66 else None
    pairs[(d["token0"], d["token1"])].append({"pool": p, "px": px, "fee": fee, "liq": liq, "factory": fac, "swaps": cnt[p]})
out = []
for (t0, t1), ps in sorted(pairs.items(), key=lambda kv: -sum(x["swaps"] for x in kv[1])):
    line = f"{sym(t0)}/{sym(t1)} pools={len(ps)}"
    print(line)
    for x in sorted(ps, key=lambda x: -x["swaps"]):
        print("   ", x["pool"], "px", f"{x['px']:.8g}", "fee", x["fee"], "liq", x["liq"], "fac", (x["factory"] or "")[:10], "swaps", x["swaps"])
    if len(ps) >= 2:
        pxs = [x["px"] for x in ps]
        print("    gap max/min bp", round((max(pxs) / min(pxs) - 1) * 1e4, 1))
    out.append({"t0": t0, "t1": t1, "s0": sym(t0), "s1": sym(t1), "pools": ps})
json.dump({"head": head, "blocks": total, "pairs": out}, open("/srv/farm/ws/scratch/r8980-pairs.json", "w"))
