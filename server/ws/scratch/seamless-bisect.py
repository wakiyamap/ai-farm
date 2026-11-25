import subprocess, json
def blk(n):
    params = json.dumps([hex(n), False])
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','base','eth_getBlockByNumber',params],capture_output=True,text=True).stdout
    b = json.loads(out)['result']
    return int(b['number'],16), int(b['timestamp'],16)
head, hts = blk(60890660)
target = hts - 7*86400
lo, hi = 60890660-3300000, head
while lo < hi-2:
    mid = (lo+hi)//2
    n, ts = blk(mid)
    if ts < target: lo = mid
    else: hi = mid
print('head', head, hts)
print('lo', lo, blk(lo)[1], 'target', target)
