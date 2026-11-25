import subprocess, json, sys
def call(m,p):
    out=subprocess.run(['python3','tools/rpc.py','arbitrum',m,json.dumps(p)],capture_output=True,text=True).stdout
    return json.loads(out)['result']
def ts(n):
    return int(call('eth_getBlockByNumber',[hex(n),False])['timestamp'],16)
latest=int(call('eth_blockNumber',[]),16)
target=ts(latest)-7*86400
print('latest',latest,'ts',ts(latest))
print('target ts',target)
lo=latest-1_900_000; hi=latest
while lo<hi:
    mid=(lo+hi)//2
    if ts(mid)<target: lo=mid+1
    else: hi=mid
print('7d-ago block',lo,ts(lo), 'latest',latest,ts(latest))
