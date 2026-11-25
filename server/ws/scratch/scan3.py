import subprocess, json, datetime, collections
A="0x00000000a55e50c71b70db3c8b58749cd1e18eb2"
T0="0x78ad7ec0e9f89e74012afa58738b6b661c024cb0fd185ee2f616c0a28924bd66"
TF="0x"+"%064x" % int("0x00000000000ba9cd9f5175108141a82b6c24d727",16)
def logs(f,t,topics):
    p={"address":A,"topics":topics,"fromBlock":hex(f),"toBlock":hex(t)}
    r=subprocess.run(['python3','tools/rpc.py','bsc','eth_getLogs',json.dumps([p])],capture_output=True,text=True)
    try: d=json.loads(r.stdout)
    except Exception: return None,(r.stdout[:120]+r.stderr[:120])
    if 'error' in d: return None,json.dumps(d['error'])[:120]
    return d['result'],None
B0=133459422; B1=134803172; CH=100000
mine=[]; total=0; err=[]
f=B0
while f<=B1:
    t=min(f+CH-1,B1)
    r1,e1=logs(f,t,[T0,None,TF])
    if e1: err.append(('mine',f,e1))
    else: mine += r1
    r2,e2=logs(f,t,[T0])
    if e2: err.append(('all',f,e2))
    else: total += len(r2)
    f=t+1
print("chunks with errors:", err)
print("OUR fills in 7d:", len(mine), " ALL fills on reactor in 7d:", total)
days=collections.Counter()
for l in mine:
    ts=int(l['blockTimestamp'],16)
    days[datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')]+=1
print("per-day:", dict(sorted(days.items())))
print("tx hashes:")
for l in mine[:25]:
    print(int(l['blockNumber'],16), datetime.datetime.utcfromtimestamp(int(l['blockTimestamp'],16)).isoformat()[:16], l['transactionHash'])
json.dump(mine, open('scratch/mine_fills.json','w'))
