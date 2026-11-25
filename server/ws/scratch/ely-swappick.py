import json, urllib.request as U
REL = "http://127.0.0.1:8545/elysium?lane=research"
POOL = "0x97796d80b6a1db786d852d6c26e107997cc5e81".replace("","")
POOL = "0x97796d80b6a1db78632f7451196b04f307329eb6"
SWAP_T0 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
def rpc(m,p):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    r=json.loads(U.urlopen(U.Request(REL,data=b,headers={"content-type":"application/json"}),timeout=60).read())
    assert "result" in r, r
    return r["result"]
head=int(rpc("eth_blockNumber",[]),16); print("head",head)
lo=head-4000
logs=rpc("eth_getLogs",[{"address":POOL,"topics":[SWAP_T0],"fromBlock":hex(lo),"toBlock":hex(head)}])
print("swap logs",len(logs),"blocks",lo,head)
best=[]
MAX=2**256-1
for lg in logs:
    d=bytes.fromhex(lg["data"][2:])
    a0=int.from_bytes(d[0:32],"big",signed=True); a1=int.from_bytes(d[32:64],"big",signed=True)
    v=abs(a0) if a0!=MAX and a1!=-(MAX) else 0
    best.append((v,lg["blockNumber"],lg["transactionHash"],a0,a1))
best.sort(reverse=True)
for b in best[:8]: print(b[0],b[1],b[2][:20],"a0",b[3],"a1",b[4])
