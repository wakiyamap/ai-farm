import json, subprocess, sys
def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','bsc',method,json.dumps(params)],capture_output=True,text=True).stdout
    return json.loads(out)['result']
def block_ts(bn):
    b = rpc('eth_getBlockByNumber',[hex(bn) if isinstance(bn,int) else bn, False])
    return int(b['timestamp'],16) if b else None
latest = int(rpc('eth_blockNumber',[]),16)
ts_now = block_ts(latest)
target = ts_now - 7*86400
lo, hi = 0, latest
# estimate using avg block time recent
b_mid_ts = block_ts(latest - 100000)
est_bpt = (ts_now - b_mid_ts)/100000
lo = max(0, latest - int(864000*1.5/est_bpt*7/10))  # rough
lo = max(0, latest - int(7*86400/est_bpt*1.2))
while lo < hi:
    mid = (lo+hi)//2
    t = block_ts(mid)
    if t < target: lo = mid+1
    else: hi = mid
print(json.dumps({'latest':latest,'ts_now':ts_now,'block7d':lo,'ts7d':block_ts(lo),'est_bpt':est_bpt}))
