"""All TOGA logs on a chain over the last N blocks (address-filtered). usage: sf_toga_logs.py <chain> <toga> <blocks_back> <step>"""
import json, subprocess, sys, time
chain, toga, back, step = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
NAMES = {"0x836808e57755d5535898b7203c7d68b1bfb2701b1943ecb133c675e0d0078015": "NewPIC",
         "0xb9c1b85a7ee70d95c61aca7cda03ef957abc5265a191ca74cc335faf59409566": "BondIncreased",
         "0x0988aefa675e81e1db7fca08264db5dc2a1cc2a604f2a78d902a9747146a5671": "ExitRateChanged"}
def rpc(method, params):
    for i in range(3):
        r = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", chain, method, json.dumps(params)], capture_output=True, text=True)
        try:
            j = json.loads(r.stdout)
            if "result" in j:
                return j
            err = j
        except Exception:
            err = {"error": r.stdout[:200]}
        time.sleep(1 + i)
    return err
head = int(rpc("eth_blockNumber", [])["result"], 16)
logs, errs, b = [], 0, head - back
while b <= head:
    e = min(b + step - 1, head)
    r = rpc("eth_getLogs", [{"address": toga, "fromBlock": hex(b), "toBlock": hex(e)}])
    if "result" in r:
        logs += r["result"]
    else:
        errs += 1
        print("err", b, e, str(r)[:160], file=sys.stderr)
        if errs > 4: break
    b = e + 1
json.dump({"head": head, "from": head - back, "errs": errs, "logs": logs}, open(f"/srv/farm/ws/scratch/sf_toga_logs_{chain}.json", "w"))
print(chain, "head", head, "from", head - back, "logs", len(logs), "errs", errs)
for l in logs:
    d = l["data"][2:]
    w = [int(d[i:i + 64], 16) for i in range(0, len(d), 64)]
    n = NAMES.get(l["topics"][0], l["topics"][0][:10])
    tok = "0x" + l["topics"][1][26:] if len(l["topics"]) > 1 else ""
    if n == "NewPIC":
        s = "pic 0x%040x bond %.6g exit/day %.6g" % (w[0], w[1] / 1e18, w[2] / 1e18 * 86400)
    elif n == "BondIncreased":
        s = "add %.6g" % (w[0] / 1e18)
    elif n == "ExitRateChanged":
        s = "exit/day %.6g" % (w[0] / 1e18 * 86400)
    else:
        s = str(w[:3])
    print(int(l["blockNumber"], 16), l["transactionHash"], n, tok, s)
