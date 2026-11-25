import subprocess, json
def rpc(method, params):
    out = subprocess.run(['python3','tools/rpc.py','base',method,json.dumps(params)],capture_output=True,text=True).stdout
    return json.loads(out)['result']
head = int(rpc('eth_blockNumber',[]),16)
target = 1794638267
lo, hi = head-4_000_000, head
# coarse then fine
while lo+1 < hi:
    mid=(lo+hi)//2
    ts=int(rpc('eth_getBlockByNumber',[hex(mid),False])['timestamp'],16)
    if ts < target: lo=mid
    else: hi=mid
    if hi-lo > 50000: step = 20000
b_lo = int(rpc('eth_getBlockByNumber',[hex(lo),False])['timestamp'],16)
b_hi = int(rpc('eth_getBlockByNumber',[hex(hi),False])['timestamp'],16)
print("head",head, "lo",lo,b_lo, "hi",hi,b_hi)
