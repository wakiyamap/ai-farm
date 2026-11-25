import json, os, urllib.request

RELAY = os.environ["RPC_RELAY_URL"]

def rpc(chain, method, params, lane="research"):
    req = urllib.request.Request(f"{RELAY}/{chain}?lane={lane}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    if "error" in d: raise RuntimeError(f"rpc error {method}: {d['error']}")
    return d["result"]

def addr_from_word(w): return "0x"+w[-40:]
def call(to, data, blk="latest"):
    return rpc("ethereum","eth_call",[{"from":"0x0000000000000000000000000000000000000000","to":to,"data":data}, blk])

FACTORY = "0x6d247b1c044fA1E22e6B04fA9F71Baf99EB29A9f"
TOPIC0 = "0xae811fae25e2770b6bd1dcb1475657e8c3a976f91d1ebf081271db08eef920af"
SEL = {"totalSupply()":"0x18160ddd","getMaturity()":"0xe16695b5","underlying()":"0x6f307dc3","isExpired()":"0x2f13b60c","decimals()":"0x313fa570","name()":"0x06fdde03","symbol()":"0x95d89b41"}

head = int(rpc("ethereum","eth_blockNumber",[]),16)
print("head",head)
logs = rpc("ethereum","eth_getLogs",[{"address":[FACTORY],"topics":[TOPIC0],"fromBlock":hex(head-720000),"toBlock":hex(head)}])
json.dump(logs, open("scratch/pendle-create-logs.json","w"))
print("logs",len(logs))
for lg in logs[-3:]:
    b=int(lg["blockNumber"],16)
    t1=addr_from_word(lg["topics"][1]); t2=addr_from_word(lg["topics"][2])
    print("log block",b,"tx",lg["transactionHash"])
    print("  t1",t1,"  t2",t2)
    for label,a in (("t1",t1),("t2",t2)):
        for fn in ("name()","symbol()","decimals()","totalSupply()","getMaturity()","isExpired()","underlying()"):
            try:
                r = call(a,SEL[fn],hex(b))
                r=r.strip()
                print(f"  {label} {fn} = {r[:100] if len(r)<=100 else r[:70]+'...'}")
            except Exception as e:
                print(f"  {label} {fn} REVERT {str(e)[:80]}")
