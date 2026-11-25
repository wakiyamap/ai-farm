import json, subprocess, sys
def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],
                         capture_output=True, text=True).stdout
    return json.loads(out)['result']
target = int(sys.argv[1])
lo, hi = 21000000, 26465298
while lo < hi:
    mid = (lo+hi)//2
    t = int(rpc('eth_getBlockByNumber',[hex(mid), False])['timestamp'],16)
    if t < target: lo = mid+1
    else: hi = mid
for b in (lo, 26465298):
    blk = rpc('eth_getBlockByNumber',[hex(b), False])
    print(b, int(blk['timestamp'],16))
