import json, urllib.request, os
URL = os.environ["RPC_RELAY_URL"] + "/ethereum?lane=research"
def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(URL, body, headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    if "error" in r: raise RuntimeError(json.dumps(r["error"])[:200])
    return r["result"]

VAULT = "0x1344a36a1b56144c3bc62e7757377d288fde0369"
ROUTER = "0x111111125421ca6dc452d289314280a0f8842a65"
# 1) same-shape active control: address-filtered, no topics, ~1000 blocks
logs = rpc("eth_getLogs", [{"address": ROUTER, "fromBlock": hex(26376000), "toBlock": hex(26376925)}])
print("1inch router last ~925 blocks:", len(logs), "logs (control non-zero)")
# 2) same vault address in the deprecation window Aug 2024 (~blocks 20.42M-20.48M)
for a,b in [(20420000,20480000),(19800000,19860000)]:
    try:
        logs = rpc("eth_getLogs", [{"address": VAULT, "fromBlock": hex(a), "toBlock": hex(b)}])
        print(f"vault {a}-{b}: {len(logs)} logs")
        from collections import Counter
        c = Counter(l["topics"][0][:10] for l in logs)
        print(" top topic0:", c.most_common(8))
    except Exception as e:
        print(a,b,"ERR",e)
