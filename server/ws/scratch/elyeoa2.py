import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def rpc(m,p=None):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p or []}).encode()
    req=urllib.request.Request(f"{URL}/elysium?lane={LANE}",b,{"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=90).read())
    if 'error' in r: print(m, r['error']); return None
    return r["result"]
T0="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
USDC="0xb47c4C8F73F009CC0C0d3f92B388d13E293F0B65"
EOA="0xf70da97812cb96acdf810712aa562db8dfa3dbef"
head=int(rpc("eth_blockNumber"),16)
t1="0x000000000000000000000000"+EOA[2:]
for label,topics in [("from EOA",[T0,t1]),("to EOA",[T0,None,t1])]:
    logs=rpc("eth_getLogs",[{"address":USDC,"topics":topics,"fromBlock":hex(head-600),"toBlock":hex(head)}])
    print(label, len(logs) if logs is not None else "ERR")
    seen=set()
    for l in (logs or [])[:4]:
        h=l['transactionHash']
        if h in seen: continue
        seen.add(h)
        tx=rpc("eth_getTransactionByHash",[h])
        rc=rpc("eth_getTransactionReceipt",[h])
        print("  to:",tx['to'],"from:",tx['from'][:12],"sel:",tx['input'][:10],"inlen:",(len(tx['input'])-10)//2,"gasUsed:",int(rc['gasUsed'],16),"status:",rc['status'])
