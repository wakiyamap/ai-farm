import json, urllib.request, os
url = os.environ["RPC_RELAY_URL"] + "/ethereum?lane=research"
def rpc(m, p):
    b = json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(url, b, {"content-type":"application/json"}), timeout=60).read())
    if "error" in r: raise RuntimeError(str(r["error"]))
    return r["result"]
head = int(rpc("eth_blockNumber", []), 16)
T_START = "0xf18b757d93c36d059284838a0328b06d8eb30d7214ffadde3266465a0006f6b3"
T_SETT  = "0x058fb1fa484531f400806f666315faf1a45941db93ba069405882b78ba40dc87"
out = {}
for name, t0 in (("started", T_START), ("settled", T_SETT)):
    logs = []
    step = 40000
    frm = head - 125000
    while frm <= head:
        to = min(frm+step-1, head)
        chunk = rpc("eth_getLogs", [{"fromBlock": hex(frm), "toBlock": hex(to), "topics":[t0]}])
        logs.extend(chunk)
        frm = to+1
    out[name] = logs
    print(name, len(logs), "head", head)
json.dump(out, open("scratch/reserve-tags.json","w"))
# summarize per contract
import collections
def u2i(x): return int(x,16)
summ = collections.defaultdict(lambda: {"started":0,"settled":0,"sells":collections.Counter(),"tokens":set(),"sizes":[]})
for k in ("started","settled"):
    for lg in out[k]:
        s = summ[lg["address"].lower()]
        s[k]+=1
        s["tokens"].add(lg["topics"][1].lower())  # trade obj? topics[1..3] are indexed trade,sell,buy? no: indexed values are addresses of trade/sell/buy
        s["tokens"].add(lg["topics"][2].lower())
        s["tokens"].add(lg["topics"][3].lower())
        if k=="started":
            s["sizes"].append([u2i(lg["data"][2+64:2+64+64]), u2i(lg["data"][2+128:2+128+64])])
print(json.dumps({a:{"started":v["started"],"settled":v["settled"],"tokens":[t for t in v["tokens"]]} for a,v in summ.items()}, indent=1))
