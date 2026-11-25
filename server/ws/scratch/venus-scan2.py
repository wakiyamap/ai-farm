import json,urllib.request,os
url=os.environ["RPC_RELAY_URL"]
def relay(method,params,chain="ethereum",lane="research"):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{url}/{chain}?lane={lane}",data=body,headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=60).read())
    if "error" in r: raise Exception(json.dumps(r["error"])[:200])
    return r["result"]
T0="0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52"
VENUS_C="0x0b9af1fd73885aD52680A1aeAa7A3f17AC702afA"
r=relay("eth_call",[{"to":VENUS_C,"data":"0xb0772d0b"},"latest"])
words=[r[2+i:i+66] for i in range(0,len(r)-2,64)][2:]
mkts=["0x"+w[24:] for w in words if len(w)==64]
head=int(relay("eth_blockNumber",[]),16)
FROM=head-648000
out=[]; page=10000; b=FROM
while b<=head:
    e=min(b+page-1,head)
    logs=relay("eth_getLogs",[{"fromBlock":hex(b),"toBlock":hex(e),"address":mkts,"topics":[T0]}])
    for L in logs:
        d=L["data"][2:]
        w=[d[i:i+64] for i in range(0,len(d),64)]
        out.append({"b":int(L["blockNumber"],16),"tx":L["transactionHash"],"addr":L["address"],
                    "liquidator":"0x"+w[0][24:],"borrower":"0x"+w[1][24:],
                    "repay":int(w[2],16),"mkt":"0x"+w[3][24:],"seize":int(w[4],16)})
    b=e+1
json.dump({"from":FROM,"head":head,"events":out},open("scratch/venus-scan2.json","w"))
print("events",len(out))
