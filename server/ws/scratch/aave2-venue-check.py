import json, urllib.request
URL = "http://127.0.0.1:8545/ethereum?lane=research"
def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    if "error" in d: raise SystemExit(f"{method}: {d['error']}")
    return d["result"]

head = int(rpc("eth_blockNumber", []), 16)
print("head", head)

steth = "0xae7ab96520de3a18e5e111b5eaab095312d7fe84"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a1abe393e73cbdc227dd"
LIQ = "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"
pool = "0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9"

code = rpc("eth_getCode", [steth, "latest"])
print("stETH code bytes:", (len(code)-2)//2)

logs = rpc("eth_getLogs", [{"address": steth, "topics":[TRANSFER],
         "fromBlock": hex(head-40000), "toBlock": hex(head)}])
print("stETH Transfer logs last 40000 blocks:", len(logs))
if logs:
    print("sample:", logs[0]["blockNumber"], logs[0]["transactionHash"])

logs2 = rpc("eth_getLogs", [{"address": pool, "topics":[LIQ],
          "fromBlock": hex(head-20000), "toBlock": hex(head)}])
print("LiquidationCall events last 20000 blocks:", len(logs2))
import collections
coll = collections.Counter()
for e in logs2[-50:]:
    d = e["data"][2:]  # drop 0x
    liq_price = int(d[0:64],16); hf=int(d[64:128],16)
    coll[e["topics"][1][:40]] += 1
    print("blk", int(e["blockNumber"],16), "coll", e["topics"][1][:40], "debt", e["topics"][2][:40], "price", liq_price, "hf", hf)
print("coll dist (last 50 events):", dict(coll))

blk = rpc("eth_getBlockByNumber", ["latest", False])
bf = blk.get("baseFeePerGas")
print("baseFeePerGas:", bf and int(bf,16)/1e9, "gwei; block", int(blk["number"],16))
