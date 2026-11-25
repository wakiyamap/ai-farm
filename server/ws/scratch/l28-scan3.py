import json, os, urllib.request, time, sys
relay=os.environ['RPC_RELAY_URL']
url=f"{relay}/base?lane=research"
TL="0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52"
TB="0x13ed6866"
TR="0x1a2a22cb"
addrs=[a.lower() for a in json.load(open("scratch/l28-addrs.json"))]
mw=["0xedc817a28e8b93b03976fbd4a3ddbc9f7d176c22","0x628ff693426583D9a7FB391E54366292F509D457"]
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
head=53907150; FR=53475151; PAGE=21600
def scan(addrs_, topic):
    out=[]; b=FR
    while b<=head:
        to=min(b+PAGE-1, head)
        logs=post({"address":addrs_,"topics":[topic],"fromBlock":hex(b),"toBlock":hex(to)})
        out.extend(logs); print(f"page {b}-{to}: {len(logs)}", file=sys.stderr); b=to+1
    return out
res={}
res["B"]=scan(addrs,TB)
res["R"]=scan(addrs,TR)
res["L"]=scan(addrs,TL)
res["MW"]=scan(mw,TL)
json.dump(res, open("scratch/l28-scan3.json","w"))
from collections import Counter
print("Borrow", len(res["B"]), "RepayBorrow", len(res["R"]), "LiquidateBorrow", len(res["L"]), "moonwell-L", len(res["MW"]))
print("L per addr:", Counter(x["address"] for x in res["L"]).most_common())
print("B per addr:", Counter(x["address"] for x in res["B"]).most_common(8))
