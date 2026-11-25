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
    for att in range(5):
        try:
            r=urllib.request.urlopen(url, data=json.dumps(p).encode(), timeout=90)
            res=json.loads(r.read())
            if "result" in res[0]: return res[0]["result"]
            msg=res[0].get("error",{}).get("message","")
        except Exception as ex:
            msg=str(ex)
        print("retry:", str(msg)[:90], file=sys.stderr); time.sleep(2)
    raise SystemExit("failed: "+str(msg)[:120])
head=53907151; FR=53475151; PAGE=21600
def scan(addrs_, topics):
    out=[]; b=FR
    while b<=head:
        to=min(b+PAGE-1, head)
        logs=post({"address":addrs_,"topics":[topics],"fromBlock":hex(b),"toBlock":hex(to)})
        out.extend(logs); print(f"page {b}-{to}: {len(logs)}", file=sys.stderr); b=to+1
    return out
dep = scan(addrs,[TB,TR,TL])
print("dep done", len(dep), file=sys.stderr)
json.dump(dep, open("scratch/l28-dep.json","w"))
mwq = scan(["0xedc817a28e8b93b03976fbd4a3ddbc9f7d176c22","0x628ff693426583D9a7FB391E54366292F509D457"],[TL])
json.dump(mwq, open("scratch/l28-mw.json","w"))
def count(dep):
    from collections import Counter
    c=Counter(x["topics"][0] if False else x.get("address") for x in [])
    tb=sum(1 for x in dep if x["data"][:32]==x["data"][:32] and x["data"]!=x["data"]) # placeholder
    return tb
# classify by event signature heuristic: Borrow data has 4 words, repay 5, liquidate 5
from collections import Counter
def sig_of(x):
    t=x["topics"][0]
    return {TB:"B",TR:"R",TL:"L"}.get(t,"?")
c=Counter(sig_of(x) for x in dep)
c2=Counter(x["address"] for x in dep)
c3=Counter(x["address"] for x in mwq)
print("dep events:", dict(c), "total", len(dep))
print("per addr top:", c2.most_common(12))
print("moonwell liquidates:", len(mwq), c3.most_common(4))
json.dump({"dep":dep,"mw":mwq}, open("scratch/l28-scan2.json","w"))
