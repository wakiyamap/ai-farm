import json, os, time, urllib.request
URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(2):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                d = json.loads(r.read())
            if "error" in d: return "ERR:"+json.dumps(d["error"])[:100]
            return d["result"]
        except Exception: time.sleep(2)
    return "EXC"
txs={"0x8bc070":"0x80dab6827d2e40679ec3f85e56b166c1d043dd9c89e9bc9efb9679c2176ff3de",
"0xa5dbea":"0x572c1a3b89fff6ea9dd1f05ff0191fea4c17657ba1ca75419695792cb68fba8c",
"0x28e2ea":"0x400106212cdece060f9c645d1c608798631682048ee742206477ed1124cdd8da",
"0x22da18":"0x166f3f533b4aff724ecfeb0c01c92d28bc21d3d1d34fdd9e58e9c2b40279347f"}
SEL={"swap(address,bool,int256,uint256,uint256,bytes)":"0x"+"38ed1739", "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)":"0x"+"18060d13",
"swapTokensForExactTokens(uint256,uint256,address[],address,uint256)":"0x"+"402e9ce5",
"swapExactTokensForETH(uint256,uint256,address[],address,uint256)":"0x"+"18386aa6",
"exactInputSingle((address,address,address,uint256,uint256,uint256))":"0x"+"b8586bf8",
"multicall(bytes[])":"0x"+"5ae9f36a","swap(uint256,uint256,bytes32,uint256,address,bytes)":None,
"approve(address,uint256)":"0x"+"095ea7b3","transfer(address,uint256)":"0x"+"a9059cbb",
"transferFrom(address,address,uint256)":"0x"+"23b872dd","pull(uint256)":"0x"+"7a77615f",
"swapTokensForExactTokens(uint256,uint256,address[],address,uint256)":None}
import collections
out={}
for k,h in txs.items():
    t=rpc("eth_getTransactionByHash",[h])
    inp=t["input"]; sel=inp[:10]; from_=t["from"]; to=t["to"]; val=t.get("value","0x0")
    names=[]
    for sig,s in SEL.items():
        if s and s[2:].lower()==sel[2:].lower(): names.append(sig)
    out[k]={"from":from_,"to":to,"sel":sel,"value":val,"match":names,"input_len":(len(inp)-2)//2,"input_head":inp[:40]}
    print(k,out[k],flush=True)
json.dump(out, open("scratch/bsc-tx-48d09.json","w"), indent=1)
