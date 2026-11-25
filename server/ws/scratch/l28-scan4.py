import json, os, urllib.request, time, sys
relay=os.environ['RPC_RELAY_URL']
url=f"{relay}/base?lane=research"
TL="0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52"
addrs=[a.lower() for a in json.load(open("scratch/l28-addrs.json"))]
def post(params):
    p=[{"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[params]}]
    for att in range(8):
        try:
            r=urllib.request.urlopen(url, data=json.dumps(p).encode(), timeout=90)
            res=json.loads(r.read())
            if "result" in res[0]: return res[0]["result"]
            msg=res[0].get("error",{}).get("message","")
        except Exception as ex:
            msg=str(ex)
        print("retry:", str(msg)[:90], file=sys.stderr); time.sleep(1.5)
    raise SystemExit("failed: "+str(msg)[:120])
head=53907150; FR=53907150-90*43200; PAGE=43200
out=[]; b=FR
while b<=head:
    to=min(b+PAGE-1, head)
    logs=post({"address":addrs,"topics":[TL],"fromBlock":hex(b),"toBlock":hex(to)})
    out.extend(logs); print(f"page {b}-{to}: {len(logs)}", file=sys.stderr); b=to+1
json.dump(out, open("scratch/l28-L90d.json","w"))
from collections import Counter
print("90d LiquidateBorrow on dep sets:", len(out))
print(Counter(x["address"] for x in out).most_common())
