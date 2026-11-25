import subprocess, json, datetime
def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','polygon',method,json.dumps(params)],capture_output=True,text=True).stdout
    env = json.loads(out)
    if 'error' in env: raise SystemExit(f'rpc error: {env["error"]}')
    return env['result']
def ts(block):
    b = rpc('eth_getBlockByNumber',[hex(block), False])
    return int(b['timestamp'],16)
head = int(rpc('eth_blockNumber',[]),16)
head_ts = ts(head)
target = head_ts - 7*86400
lo, hi = head - 8*86400*3, head
while lo < hi:
    mid = (lo+hi)//2
    if ts(mid) < target: lo = mid+1
    else: hi = mid
u = lambda t: datetime.datetime.utcfromtimestamp(t).isoformat()
print(json.dumps({'head':head,'head_ts':head_ts,'head_date':u(head_ts),'block7d':lo,'block7d_ts':ts(lo),'block7d_date':u(ts(lo))}))
