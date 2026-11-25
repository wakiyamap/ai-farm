import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def rpc(m,p=None):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p or []}).encode()
    req=urllib.request.Request(f"{URL}/elysium?lane={LANE}",b,{"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=90).read())['result']
    return r
import re
for a,out in [("0x4cd00e387622c35bddb9b4c962c136462338bc31","scratch/code4cd.hex"),
              ("0x047b4355b8497b6588d38f39057d129478bdd3e8","scratch/code047.hex")]:
    c=rpc("eth_getCode",[a,"latest"])
    open(out,"w").write(c)
    body=c[2:]
    sels=set(m.group(1) for m in re.finditer(r"63([0-9a-f]{8})81(?:14|...)", body))
    # broader solc dispatch pattern: PUSH4 sel ... EQ ... JUMPI
    sels2=set(m.group(1) for m in re.finditer(r"63([0-9a-f]{8})60", body))
    print(a[:10], "code", len(body)//2, "sel(pat1)", len(sels), "sel(pat6360)", len(sels2))
    open(out+".sels","w").write("\n".join(sorted(sels2)))
