import json, os, time, urllib.request

URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            if "error" in d:
                return "ERR:"+json.dumps(d["error"])[:80]
            return d["result"]
        except Exception as e:
            time.sleep(2)
    return "EXC"

addrs = ["0x55d398326f99059ff775485246999027b3197955","0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c",
"0x6b30b5d2bf5e9f2e62904c3493052ad1664da0fa","0xb9951e18bf97054703e18dddf753eee7460104e1",
"0x5d3a12c42e5372b2cc3264ab3cdcf660a1555238","0x44dd94ce8ae0537a529e95ea9d997ef20825f1bf",
"0xd1e10775f931a711032dbf4c18494b57b650a417","0x330122ce76c44dba4e7f2a2ff3e3206ab9e66fd7",
"0x1feb1b0afcee64cc445392922a2d043ba3e5dbb2","0x3f673b5371ae833355f538eb868c7e8ff135c1b0"]
NAME="0x"+"06fdde03"+"0"*56  # name() padded? no: selector only
res={}
for a in addrs:
    name=rpc("eth_call",[{"to":a,"data":"0x06fdde03"},"latest"])
    if isinstance(name,str) and name.startswith("0x") and not name.startswith("ERR"):
        # decode string
        try:
            h=name[2:]
            ln=int(h[64:128],16)
            txt=bytes.fromhex(h[128:128+ln*2]).decode("utf8","replace")
        except Exception as e:
            txt=name[:20]
        res[a]=("name",txt)
    else:
        code=rpc("eth_getCode",[a,"latest"])
        res[a]=("code_len",(len(code)-2)//2 if code and not str(code).startswith("ERR") else str(code)[:60])
    print(a,res[a])
json.dump(res, open("scratch/bsc-ident-48d09.json","w"))
