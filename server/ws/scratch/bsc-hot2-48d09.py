import json, os, urllib.request
URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            if "error" in d: continue
            return d["result"]
        except Exception: pass
    return None
picks=json.load(open("scratch/bsc-hotpicks-48d09.json"))
SEL={"swapExactTokensForTokens(uint256,uint256,address[],address,uint256)":"18060d13","swap(address,bool,int256,uint256,uint256,bytes)":"38ed1739","multicall(bytes[])":"5ae9f36a","transfer(address,uint256)":"a9059cbb","approve(address,uint256)":"095ea7b3","swapExactTokensForTokensSimple(...)":"0d032e07","pull(uint256)":"7a77615f"}
res={}
for c,p in picks.items():
    t=rpc("eth_getTransactionByHash",[p["hash"]])
    sel=t["input"][:10].lower()
    names=[k for k,v in SEL.items() if v==sel[2:]]
    code=rpc("eth_getCode",[t["to"],"latest"])
    res[c]={"tx_to":t["to"],"tx_from":t["from"],"sel":sel,"fn":names,"input_len":(len(t["input"])-2)//2,"to_code_len":(len(code)-2)//2 if code else -1}
    print(c,res[c],flush=True)
json.dump(res, open("scratch/bsc-hot2-48d09.json","w"), indent=1)
