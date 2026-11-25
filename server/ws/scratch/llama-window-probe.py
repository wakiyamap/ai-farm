#!/usr/bin/env python3
import json, urllib.request, os, sys
RELAY=os.environ.get("RPC_RELAY_URL","http://127.0.0.1:8545")
def rpc(chain, method, params, lane="research"):
    req=urllib.request.Request(f"{RELAY}/{chain}?lane={lane}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=30).read())
    if "error" in r: raise RuntimeError(json.dumps(r["error"]))
    return r["result"]
def call(to, data, block, chain="ethereum"):
    return rpc(chain,"eth_call",[{"to":to,"from":"0x0000000000000000000000000000000000000000","data":data},hex(block)])
SEL="0x042e02cf"
def isliq(to,user,block):
    d=SEL+user[2:].lower().rjust(64,"0")
    out=call(to,d,block)
    return out, int(out[-2:],16)==1 if len(out)==66 else None
EVENTS=[
 ("0xeda215b7666936ded834f76f3fbc6f323295110a","0xe5b2a2459914b78f52bef1d294605efc91e311a3",26343051),
 ("0xcad85b7fe52b1939dceebee9bcf0b2a5aa0ce617","0xcd48996795e10903787a2f6bf8730f6368a8fd0a",26338885),
]
out={}
for to,user,B in EVENTS:
    res={"controller":to,"user":user,"capture":B,"probe":{}}
    for off in (1,2,3,5,8,13,21,34,55,89,144,233):
        b=B-off
        try:
            raw,v=isliq(to,user,b)
            res["probe"][str(off)]={"blk":b,"raw":raw[:68],"liq":v}
        except Exception as e:
            res["probe"][str(off)]={"blk":b,"err":str(e)[:120]}
            break
    out[f"{B}"]={k:v for k,v in res.items()}
# positive control: same controller scan returns >=1 log in same window (batch check)
TOPIC="0x642dd4d37ddd32036b9797cec464c0045dd2118c549066ae6b0f88e32240c2d0"
for to,user,B in EVENTS:
    try:
        logs=rpc("ethereum","eth_getLogs",[{"address":to,"topics":[TOPIC],"fromBlock":hex(B-300),"toBlock":hex(B+2)}],lane="research")
        out[f"{B}"]["same_ctrl_logs"]=[{"block":int(l["blockNumber"],16),"tx":l["transactionHash"][:14]} for l in logs]
    except Exception as e:
        out[f"{B}"]["getlogs_err"]=str(e)[:150]
json.dump(out,open("scratch/llama-window-probe.json","w"),indent=1)
print(json.dumps(out,indent=1)[:2400])
