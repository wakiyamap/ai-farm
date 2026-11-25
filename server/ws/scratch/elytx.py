import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def rpc(m,p=None):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p or []}).encode()
    req=urllib.request.Request(f"{URL}/elysium?lane={LANE}",b,{"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=60).read())
    if 'error' in r: return None
    return r["result"]
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
USDC="0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65"
head=int(rpc("eth_blockNumber"),16)
for r_ in ["0x5567954cd026cebfe486062cb75848e0f1c12e58","0x047b4355b8497b6588d38f39057d129478bdd3e8"]:
    t1="0x000000000000000000000000"+r_[2:]
    logs=rpc("eth_getLogs",[{"address":USDC,"topics":[T0,t1],"fromBlock":hex(head-1000),"toBlock":hex(head)}])
    print(r_[:10], "logs as from:", len(logs) if logs else 0)
    for l in (logs or [])[:2]:
        tx=rpc("eth_getTransactionByHash",[l['transactionHash']])
        if logs:
            inp=tx['input']; print("  tx to",tx['to'],"from",tx['from'][:10],"input",inp[:8],"len",len(inp)//2-10)
