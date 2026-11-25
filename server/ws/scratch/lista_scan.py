import json, subprocess, sys, re
from concurrent.futures import ThreadPoolExecutor

LATEST = int(sys.argv[1])
FROM = LATEST - 1_344_000
CHUNK = 5000
MOOLAH = "0x8F73b65B4caAf64FBA2aF91cC5D4a2A1318E5D8C"
PUBLIQ = "0x882475d622c687b079f149b69a15683fcbecc6d9"
T0A = "0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41"  # Moolah Liquidate
T0B = "0xc825af5ed71c3d4e8384fad1414973f60116d9c9ff5a485f91bb499802bd8e27"  # PublicLiquidator Liquidated

ranges = []
b = FROM
while b <= LATEST:
    ranges.append((b, min(b + CHUNK - 1, LATEST)))
    b += CHUNK

def fetch(r):
    lo, hi = r
    params = json.dumps([{"address": [MOOLAH, PUBLIQ],
                          "topics": [[T0A, T0B]],
                          "fromBlock": hex(lo), "toBlock": hex(hi)}])
    for attempt in range(4):
        p = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "bsc", "eth_getLogs",
                            params, "--lane", "research"], capture_output=True, text=True)
        if p.returncode == 0:
            try:
                d = json.loads(p.stdout)
                if "result" in d:
                    return lo, d["result"]
            except Exception:
                pass
        p_err = p.stderr[-200:] if p.stderr else ""
    return lo, {"error": p_err}

logs = []
errors = []
with ThreadPoolExecutor(max_workers=6) as ex:
    for lo, res in ex.map(fetch, ranges):
        if isinstance(res, dict):
            errors.append((lo, res))
        else:
            logs.extend(res)

m_liq = [l for l in logs if l["address"].lower() == MOOLAH.lower()]
p_liq = [l for l in logs if l["address"].lower() == PUBLIQ.lower()]

def caller(t): return "0x" + t[2][-40:]   # topics: sig, id, caller, borrower
callers = {}
for l in m_liq:
    a = caller(l["topics"])
    amt = int(l["data"][2:66], 16)  # repaidAssets
    callers[a] = callers.get(a, [0, 0])
    callers[a][0] += 1
    callers[a][1] = max(callers[a][1], amt)

samples = sorted(m_liq, key=lambda l: int(l["data"][2:66], 16), reverse=True)[:6]
out = {
    "latest": LATEST, "from": FROM, "chunks": len(ranges),
    "chunk_errors": errors[:5], "n_chunk_errors": len(errors),
    "moolah_liquidate_count": len(m_liq),
    "public_liquidated_count": len(p_liq),
    "distinct_callers_moolah": len(callers),
    "callers": {a: v for a, v in sorted(callers.items(), key=lambda kv: -kv[1][0])[:30]},
    "top_samples": [{"tx": l["transactionHash"], "blk": int(l["blockNumber"], 16),
                     "caller": caller(l["topics"]), "repaid": int(l["data"][2:66], 16),
                     "seized": int(l["data"][2+2*64:2+3*64], 16),
                     "id": l["topics"][1][-64:]} for l in samples],
    "pub_events": [{"tx": l["transactionHash"], "data": l["data"]} for l in p_liq][:20],
}
json.dump(out, open("/srv/farm/ws/scratch/lista_scan_out.json", "w"), indent=1)
print(json.dumps(out, indent=1)[:3500])
