import subprocess, json, datetime, collections
A="0x00000000a55e50c71b70db3c8b58749cd1e18eb2"
T0="0x78ad7ec0e9f89e74012afa58738b6b661c024cb0fd185ee2f616c0a28924bd66"
TF="0x"+"%064x" % int("0x00000000000ba9cd9f5175108141a82b6c24d727",16)
def logs(f,t,topics):
    p={"address":A,"topics":topics,"fromBlock":hex(f),"toBlock":hex(t)}
    r=subprocess.run(['python3','tools/rpc.py','bsc','eth_getLogs',json.dumps([p])],capture_output=True,text=True)
    try: d=json.loads(r.stdout)
    except Exception: return None,(r.stdout[:100]+r.stderr[:100])
    return (d.get('result'), json.dumps(d.get('error'))[:100] if 'error' in d else None)
# 30d window: latest ts 1795226286 -> 30d = 2592000 s -> /0.45 s per block
B1=134803172; B30=134803172-int(2592000/0.45)
print('30d start block', B30, 'end', B1)
mine=[]; allc=0
f=B30
while f<=B1:
    t=min(f+300000-1,B1)
    r,e=logs(f,t,[T0,None,TF])
    if r is None:
        # shrink
        r,e=logs(f,min(f+100000-1,B1),[T0,None,TF]); 
        if r is None: print('ERR',f,e); break
    mine+=r
    f=t+1
print('our fills in 30d:', len(mine))
for l in mine[:20]:
    print(int(l['blockNumber'],16), datetime.datetime.fromtimestamp(int(l['blockTimestamp'],16),datetime.UTC).strftime('%m-%d %H:%M'), l["transactionHash"])
