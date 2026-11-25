import subprocess, json, sys
def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True).stdout
    return json.loads(out)['result']
target = int(sys.argv[1])
lo, hi = 26400000, 26463947
while lo < hi:
    mid = (lo+hi)//2
    ts = int(rpc('eth_getBlockByNumber',[hex(mid),False])['timestamp'],16)
    if ts < target: lo = mid+1
    else: hi = mid
b = rpc('eth_getBlockByNumber',[hex(lo),False])
print(lo, int(b['timestamp'],16), b['timestamp'])
