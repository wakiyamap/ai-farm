import subprocess, json, collections, datetime
A="0x00000000a55e50c71b70db3c8b58749cd1e18eb2"
T0="0x78ad7ec0e9f89e74012afa58738b6b661c024cb0fd185ee2f616c0a28924bd66"
def logs(f,t):
    p={"address":A,"topics":[T0],"fromBlock":hex(f),"toBlock":hex(t)}
    r=subprocess.run(['python3','tools/rpc.py','bsc','eth_getLogs',json.dumps([p])],capture_output=True,text=True)
    d=json.loads(r.stdout); return d.get('result')
c=collections.Counter()
f=133459422; B1=134803172
while f<=B1:
    t=min(f+100000-1,B1)
    r=logs(f,t)
    if r is None: print('err',f); break
    for l in r:
        c['0x'+l['topics'][2][-40:]]+=1
    f=t+1
print('distinct fillers in 7d:', len(c), 'total fills:', sum(c.values()))
for a,n in c.most_common(15): print(a,n)
