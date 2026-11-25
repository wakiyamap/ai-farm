import json, subprocess, datetime

def rpc(m,p):
    o=subprocess.run(['python3','tools/rpc.py','base',m,json.dumps(p)],capture_output=True,text=True).stdout
    try: d=json.loads(o)
    except Exception: return {'__raw__': o[:200]}
    return d.get('result', d)

HEAD=60930588
HUB="0x783251f103555068c1e9d755f69458f39ed937c0"
FRESH="0x00000000000000000000000000000000BEEF0001"
BIGV="0xb98840b22618e77bbd0403c81365eefc7d449559"   # biggest vault (26.39 WETH per subgraph)
V2="0x1baeb82f78f55c793296e7153f2b45396ceaeb4b"     # vault with the 2 logs 2026-10-11

def ts(n):
    b=rpc('eth_getBlockByNumber',[hex(n),False])
    return datetime.datetime.fromtimestamp(int(b['timestamp'],16),datetime.UTC).isoformat()

# 1) earlier hub windows (same shape, no topics) to date last activity
for f,t in [(25000000,35000000),(35000000,45000000),(45000000,50405573),(50405573,57906587)]:
    r=rpc('eth_getLogs',[{'address':HUB,'fromBlock':hex(f),'toBlock':hex(t)}])
    n=len(r) if isinstance(r,list) else r
    print(f"hub {f}-{t} ({ts(f)[:10]}..{ts(t)[:10]}): {n if isinstance(n,int) else n}")
    if isinstance(r,list) and r:
        last=r[-1]; print("   last log block",int(last['blockNumber'],16), ts(int(last['blockNumber'],16)),
                          "topic0",last['topics'][0][:10], "n_topics",len(last['topics']))
