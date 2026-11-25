import json, subprocess, datetime

def rpc(method, params):
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr or p.stdout)
    j=json.loads(p.stdout)
    if 'error' in j: raise RuntimeError(j['error'])
    return j['result']

head=int(rpc('eth_blockNumber',[]),16)
end=rpc('eth_getBlockByNumber',[hex(head),False])
endtime=int(end['timestamp'],16)
target=endtime-7*86400
lo=head-60000; hi=head
while lo+1<hi:
    mid=(lo+hi)//2
    b=rpc('eth_getBlockByNumber',[hex(mid),False])
    if int(b['timestamp'],16)<target: lo=mid
    else: hi=mid
start=rpc('eth_getBlockByNumber',[hex(hi),False])
print('window',hi,datetime.datetime.fromtimestamp(int(start['timestamp'],16),datetime.timezone.utc).isoformat(),head,datetime.datetime.fromtimestamp(endtime,datetime.timezone.utc).isoformat(),flush=True)
raw=rpc('eth_call',[{'to':'0x4dCf7407AE5C07f8681e1659f626E114A7667339','data':'0xb0772d0b'},'latest'])
s=raw[2:]; n=int(s[64:128],16); markets=['0x'+s[128+i*64+24:128+(i+1)*64] for i in range(n)]
print('markets',n,markets,flush=True)
topic='0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'
for a in range(hi,head+1,3000):
    z=min(a+2999,head)
    logs=rpc('eth_getLogs',[{'address':markets,'fromBlock':hex(a),'toBlock':hex(z),'topics':[topic]}])
    if logs: print('liquidations',a,z,len(logs),[(x['address'],x['transactionHash'],int(x['blockNumber'],16)) for x in logs[:5]],flush=True)
print('done')
