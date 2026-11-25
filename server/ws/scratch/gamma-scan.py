import json, subprocess, tempfile, os, sys
def rpc(method, params, tries=4):
    err=None
    for t in range(tries):
        f=tempfile.NamedTemporaryFile("w",suffix=".json",delete=False)
        json.dump(params,f); f.close()
        r=subprocess.run(["python3","tools/rpc.py","polygon",method,"--params-file",f.name],capture_output=True,text=True)
        os.unlink(f.name)
        try: d=json.loads(r.stdout)
        except Exception: d={"error":{"message":(r.stdout+r.stderr)[:200]}}
        if "error" not in d: return d["result"]
        err=d["error"]
    print("ERR",json.dumps(err)[:200], flush=True); return None

info=json.load(open("scratch/gamma-vault-info.json"))
vaults=[x["vault"] for x in info if x["totalSupply"]>0]
FROM,B=97236386,97638786
TOPIC="0xbc4c20ad04f161d631d9ce94d27659391196415aa3c42f6a71c62e905ece782d"
logs=[]
CHUNK=100000
reqs=0
for i in range(0,len(vaults),32):
    batch=vaults[i:i+32]
    f0=FROM
    while f0<=B:
        f1=min(f0+CHUNK-1,B)
        res=rpc("eth_getLogs",[{"fromBlock":hex(f0),"toBlock":hex(f1),"address":batch,"topics":[TOPIC]}])
        reqs+=1
        if res is None:
            # split chunk in half once
            mid=(f0+f1)//2
            for (g0,g1) in [(f0,mid),(mid+1,f1)]:
                res2=rpc("eth_getLogs",[{"fromBlock":hex(g0),"toBlock":hex(g1),"address":batch,"topics":[TOPIC]}])
                reqs+=1
                if res2: logs+=res2
            f0=f1+1
            continue
        logs+=res
        f0=f1+1
print("reqs",reqs,"logs",len(logs))
json.dump(logs,open("scratch/gamma-rebalance-logs.json","w"))
txs=sorted(set(l["transactionHash"] for l in logs))
vset=sorted(set(l["address"] for l in logs))
print("distinct txs",len(txs),"vaults with rebalances",len(vset))
# decode feeAmount0/1 (data words 4,5 => idx 3,4 zero-based)
nz=[l for l in logs if int(l["data"][2:66],16) or int(l["data"][66:130],16)]
print("logs with nonzero feeAmount0/1:",len(nz))
for l in logs[:3]: print(l["blockNumber"],l["address"],l["transactionHash"])
