import json, urllib.request, os, time
URL = os.environ["RPC_RELAY_URL"]; LANE="research"
def rpc(chain, method, params):
    req = urllib.request.Request(f"{URL}/{chain}?lane={LANE}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["result"]
head = int(rpc("hyperevm","eth_blockNumber",[]),16)
print("head", head)
import collections
senders = collections.Counter(); pairs = collections.Counter(); txs_total=0
samples=[]
w=20
for i in range(5):
    hi = head-200-1440*i   # windows spread ~8h, older bound first
    for b in range(hi, hi+w):
        blk = rpc("hyperevm","eth_getBlockByNumber",[hex(b), True])
        if blk is None: continue
        for t in blk["transactions"]:
            s=t["from"].lower()
            senders[s]+=1
            if t.get("to"): pairs[(s,t["to"].lower())]+=1
            txs_total+=1
    samples.append((hi,hi+w-1))
    time.sleep(0.2)
print("windows", samples, "txs", txs_total)
print("top senders:")
for s,c in senders.most_common(18):
    print(f"  {s} {c}")
print("top pairs:")
for (s,d),c in pairs.most_common(12):
    print(f"  {s} -> {d} {c}")
