"""Superfluid AgreementLiquidatedV2 scan (topic-only; emitted by each SuperToken).
usage: sf_scan.py <chain> <blocks_back> <step> [out]
"""
import json, subprocess, sys, collections

T0 = "0xb8381a3ce157650e06186e3e8f4dd4dc29236f2688b6eed1893d0a60d7c6386f"
chain, back, step = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
out = sys.argv[4] if len(sys.argv) > 4 else f"/srv/farm/ws/scratch/sf_logs_{chain}.json"


def rpc(method, params):
    r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", chain, method, json.dumps(params)],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"error": r.stdout[:200] + r.stderr[:200]}


head = int(rpc("eth_blockNumber", [])["result"], 16)
logs = []
errs = 0
b = head - back
while b <= head:
    e = min(b + step - 1, head)
    r = rpc("eth_getLogs", [{"fromBlock": hex(b), "toBlock": hex(e), "topics": [T0]}])
    if "result" not in r:
        errs += 1
        print("err", b, e, str(r)[:200], file=sys.stderr)
        if errs > 5:
            break
    else:
        logs += r["result"]
    b = e + 1
json.dump({"head": head, "from": head - back, "logs": logs, "errs": errs}, open(out, "w"))
print(chain, "head", head, "from", head - back, "logs", len(logs), "errs", errs)
liq = collections.Counter()
tok = collections.Counter()
for l in logs:
    d = l["data"][2:]
    w = [d[i:i + 64] for i in range(0, len(d), 64)]
    liquidator = "0x" + l["topics"][2][26:]
    rr = "0x" + w[1][24:]
    amt = int(w[2], 16)
    delta = int(w[3], 16)
    if delta >= 2 ** 255:
        delta -= 2 ** 256
    liq[(liquidator, rr == liquidator)] += 1
    tok[l["address"]] += 1
    print(int(l["blockNumber"], 16), l["transactionHash"], "tok", l["address"], "liq", liquidator, "rcv", rr, "amt", amt, "delta", delta)
print("liquidators (addr, got_reward):", liq.most_common(15))
print("tokens:", tok.most_common(15))
