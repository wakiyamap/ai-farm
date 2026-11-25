import json, urllib.request, os, re, collections
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
# 1) claim amounts to EOA
t2="0x000000000000000000000000"+EOA[2:]
logs=rpc("eth_getLogs",[{"address":USDC,"topics":[T0,None,t2],"fromBlock":hex(head-20000),"toBlock":hex(head)}])
vals=[int(l['data'],16)/1e6 for l in (logs or [])]
print("to-EOA USDC claims in 20k blocks:", len(vals), [round(v,2) for v in vals[:10]])
# 2) token()/slot0 probes on remaining candidates
S={'token()':'0xfc0c546a','slot0()':'0x3850c7bd'}
for a in ["0x0729e2a4716d9f7dd17858d5d504426d228697f7","0x195627f03fe2668d65c763cd39eec45b1d76c8ee",
"0xb2766443c2f92fbe579f057593802737bc88f591","0x8f10b468b06c6fd214b65f87778827f7d113f996",
"0x939e398d2c31b0757d009222de99c6e461d3de15","0x5ae4cc63202a292fd948ff957f5c3f29c50c77ab"]:
    out=[]
    for n,d in S.items():
        r=rpc("eth_call",[{"to":a,"data":d},"latest"])
        out.append(f"{n}:{str(r)[:14] if r and not isinstance(r,dict) else 'rv'}")
    print(a[:12], " | ".join(out))
