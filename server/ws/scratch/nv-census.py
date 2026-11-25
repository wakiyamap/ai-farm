import json, urllib.request, os, time
URL = os.environ["RPC_RELAY_URL"] + "/ethereum?lane=research"
def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(URL, body, headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    if "error" in r: raise RuntimeError(json.dumps(r["error"])[:200])
    return r["result"]

head = int(rpc("eth_blockNumber", []), 16)
VAULT = "0x1344a36a1b56144c3bc62e7757377d288fde0369"
code = rpc("eth_getCode", [VAULT, "latest"])
print("head", head, "vault code bytes", (len(code)-2)//2)

out = {}
# all-logs census on the vault proxy over ~10-day windows
start = head - 126000  # 10 d
while start < head:
    end = min(start + 63000, head)  # ~4.4 d pages
    logs = rpc("eth_getLogs", [{"address": VAULT, "fromBlock": hex(start), "toBlock": hex(end)}])
    out[f"{start}-{end}"] = len(logs)
    for lg in logs[:200]:
        t = lg["topics"][0]
        rec = {"block": int(lg["blockNumber"],16), "tx": lg["transactionHash"], "topic0": t[:10], "data": lg["data"][:80]}
        print(json.dumps(rec))
    start = end
print(json.dumps(out))
