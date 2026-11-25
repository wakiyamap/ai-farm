import subprocess, json, sys
def call(chain, method, params):
    out=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py",chain,method,json.dumps(params)],capture_output=True,text=True).stdout
    return json.loads(out)["result"]
def ts(chain, block):
    b=call(chain,"eth_getBlockByNumber",[hex(block),False])
    return int(b['timestamp'],16), int(b['number'],16)
def find_block(chain, target, hi):
    lo=hi-1
    while lo<hi-1:
        mid=(lo+hi)//2
        t,_=ts(chain,mid)
        if t>target: hi=mid
        else: lo=mid
    return hi
