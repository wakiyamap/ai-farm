import json, os, sys, urllib.request

RELAY = os.environ["RPC_RELAY_URL"]

def rpc(chain, method, params, lane="research"):
    req = urllib.request.Request(f"{RELAY}/{chain}?lane={lane}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    if "error" in d: raise SystemExit(f"rpc error {method}: {d['error']}")
    return d["result"]

def call(addr, data, blk="latest"):
    return rpc("ethereum","eth_call",[{"to":addr,"data":data}, blk])

FACTORY = "0x6d247b1c044fA1E22e6B04fA9F71Baf99EB29A9f"
TOPIC0 = "0xae811fae25e2770b6bd1dcb1475657e8c3a976f91d1ebf081271db08eef920af"

head = int(rpc("ethereum","eth_blockNumber",[]),16)
print("head",head)
logs = rpc("ethereum","eth_getLogs",[{"address":[FACTORY],"topics":[TOPIC0],"fromBlock":hex(head-720000),"toBlock":hex(head)}])
print("logs",len(logs))
sel = {"totalSupply":"0x18160ddd","getMaturity":"0x5f0f0fd3"}  # placeholder
import hashlib
def keccak4(sig):
    # not available; hardcode measured selectors
    d = {"totalSupply()":"18160ddd","getMaturity()":"e16695b5","underlying()":"6f307dc3","isExpired()":"2f13b60c","redeem(address,uint256)":"1e9a6950","decimals()":"313fa570","name()":"06fdde03"}
    return "0x"+d[sig]
import datetime
for lg in logs[-3:]:
    b=int(lg["blockNumber"],16); t=lg["transactionHash"]
    t1=lg["topics"][1]; t2=lg["topics"][2] if len(lg["topics"])>2 else None
    print("log",b,t,"t1",t1,"t2",t2,"data",lg["data"])
    for label,a in (("t1",t1),("t2",t2)):
        if not a: continue
        for fn in ("totalSupply()","getMaturity()","underlying()","isExpired()","decimals()"):
            try:
                r = call(a,keccak4(fn),hex(b))
                print(" ",label,a,fn,"=",r[:80])
            except Exception as e:
                print(" ",label,a,fn,"REVERT", str(e)[:60])
