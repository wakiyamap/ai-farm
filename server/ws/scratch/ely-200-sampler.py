"""Lead 200: 60-min (truncated to session) USDC/WHYPE multi-venue mid sampler, Elysium.
One JSON-RPC batch per ~2 s; writes JSONL rounds + summary. Research lane. 0 fork, 0 tx."""
import json, urllib.request, os, subprocess, time, sys
from datetime import datetime, timezone

RELAY = os.environ["RPC_RELAY_URL"] + "/elysium"
USDC = "0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65"
SV = "0x27eD73aE0652fdCf71d6793412A7525f32bE9dfE"
DUR_MIN = float(sys.argv[1]) if len(sys.argv) > 1 else 33.0
OUT = "/srv/farm/ws/scratch/ely-200-samples.jsonl"
SUM = "/srv/farm/ws/scratch/ely-200-summary.txt"

POOLS = [
    ("aero100", "v3", "0x97796d80b6a1db78632f7451196b04f307329eb6"),   # token0=USDC, dyn fee via fee()
    ("ramses", "v3", "0xd329b88ba62483918c3f6c9421178345cf9eebc2"),     # token0=USDC, dyn fee via fee()
    ("metric15", "omm", "0xcd82337e7d2d1ab66699457a8e25b4d8e78ca259"),  # getSellAndBuyPrices
    ("metric19", "omm", "0xef3ac7034eac6bf3b37d3a78b6a510c7c8ac53c0"),
    ("avrA", "v4", "0x93063b58e11b38f8bdf915b863148a32561ed4e0e6027c3a019cc0c980968be5"),  # poolId, ts50
    ("avrB", "v4", "0x7bc032d75b742560db1a08dad3599623e39beae42856b592e132c0b498a62752"),  # poolId, ts10
]

def cd(sig, *args):
    return subprocess.run(["/opt/foundry/bin/cast", "calldata", sig, *[str(a) for a in args]],
                          capture_output=True, text=True).stdout.strip()

SEL = {k: cd(*v) if isinstance(v, tuple) else cd(v) for k, v in {
    "slot0": "slot0()", "fee": "fee()", "sbsp": "getSellAndBuyPrices()",
    "gs0": ("getSlot0(bytes32)", "0x" + "0" * 64), "gas": cd("getSlot0(bytes32)", POOLS[4][2]),
}.items()}

def post(body):
    req = urllib.request.Request(RELAY, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read())

def word(v, i=0):
    return int(v[2 + i * 64:2 + (i + 1) * 64 + 2 - 2 * (i == 0 and 0)], 16)

def words(v):
    n = (len(v) - 2) // 64
    return [int(v[2 + j * 64:2 + (j + 1) * 64], 16) for j in range(n)]

def v3_usdc_per_whype(sqrt_raw):
    # token0=USDC(6) token1=WHYPE(18): raw price = WHYPEperUSDC*1e-12 -> USDC/WHYPE = 1e12/raw? No:
    # raw = (sqrt/2^96)^2 = token1per0 raw; human WHYPE/USDC = raw*1e6/1e18 = raw*1e-12; USDC/WHYPE = 1e12/raw*1e24*1e-24 -> just: 1/(raw*1e-12)*1 -> 
    return 1.0 / (sqrt_raw * 1e-12) if sqrt_raw else 0.0

start = time.time()
deadline = start + DUR_MIN * 60
round_i = 0
out = open(OUT, "a")
log = open(SUM, "a")
def plog(m):
    line = datetime.now(timezone.utc).strftime("%H:%M:%S") + " " + m
    log.write(line + "\n"); log.flush()

plog(f"sampler start pools={[p[0] for p in POOLS]} dur_min={DUR_MIN}")
while time.time() < deadline:
    t0 = time.time()
    round_i += 1
    calls = []
    idx = {}
    for name, kind, addr in POOLS:
        if kind == "v3":
            idx[name + "_s0"] = len(calls) + 1; calls.append({"jsonrpc": "2.0", "id": len(calls) + 1, "method": "eth_call", "params": [{"to": addr, "data": SEL["slot0"]}, "latest"]})
            idx[name + "_fee"] = len(calls) + 1; calls.append({"jsonrpc": "2.0", "id": len(calls) + 1, "method": "eth_call", "params": [{"to": addr, "data": SEL["fee"]}, "latest"]})
        elif kind == "omm":
            idx[name] = len(calls) + 1; calls.append({"jsonrpc": "2.0", "id": len(calls) + 1, "method": "eth_call", "params": [{"to": addr, "data": SEL["sbsp"]}, "latest"]})
        else:
            idx[name] = len(calls) + 1; calls.append({"jsonrpc": "2.0", "id": len(calls) + 1, "method": "eth_call", "params": [{"to": SV, "data": cd("getSlot0(bytes32)", addr)}, "latest"]})
    idx["blk"] = len(calls) + 1; calls.append({"jsonrpc": "2.0", "id": len(calls) + 1, "method": "eth_blockNumber", "params": []})
    if round_i % 60 == 1:
        idx["gp"] = len(calls) + 1; calls.append({"jsonrpc": "2.0", "id": len(calls) + 1, "method": "eth_gasPrice", "params": []})
    try:
        res = post(calls)
        by = {x["id"]: x.get("result") for x in res}
        rec = {"t": round(t0, 3), "ts": datetime.now(timezone.utc).isoformat(), "blk": int(by[idx["blk"]], 16) if by.get(idx["blk"]) else None, "p": {}, "f": {}}
        if "gp" in idx and by.get(idx["gp"]): rec["gwei"] = int(by[idx["gp"]], 16) / 1e9
        for name, kind, addr in POOLS:
            if kind == "v3":
                v = by.get(idx[name + "_s0"])
                f = by.get(idx[name + "_fee"])
                if v:
                    r = (int(v[2:66], 16) / 2**96) ** 2
                    rec["p"][name] = 1e12 * (r / 1e24) * 1e12 if False else 1.0 / (r * 1e-12)
                rec["f"][name] = int(f, 16) if f else None
            elif kind == "omm":
                v = by.get(idx[name])
                if v:
                    w = words(v)
                    rec["p"][name] = (w[0] + w[1]) / 2e18 / 18.446744073709551616e-19 * 1e-18 * 1e18 if False else (w[0] + w[1]) / 2.0 / 1.8446744073709551616e19
                    rec["p"][name + "_b"] = w[0] / 1.8446744073709551616e19; rec["p"][name + "_a"] = w[1] / 1.8446744073709551616e19
            else:
                v = by.get(idx[name])
                if v:
                    w = words(v)
                    r = (w[0] / 2**96) ** 2
                    rec["p"][name] = 1.0 / (r * 1e-12)
                    rec["p"][name + "_liq"] = w[1]
        out.write(json.dumps(rec) + "\n"); out.flush()
        if round_i % 300 == 1:
            plog(f"round {round_i} blk={rec.get('blk')} aero100={rec['p'].get('aero100'):.4f} ramses={rec['p'].get('ramses'):.4f}")
    except Exception as e:
        plog(f"round {round_i} ERR {str(e)[:100]}")
        time.sleep(5)
    if round_i % 60 == 1 and "gp" in idx:
        pass
    # keep 2 s cadence
    el = time.time() - t0
    if el < 2.0: time.sleep(2.0 - el)
plog(f"sampler end rounds={round_i} dur_min={(time.time()-start)/60:.1f}")
out.close(); log.close()
