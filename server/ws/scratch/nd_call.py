import subprocess, json, sys
def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True).stdout
    d = json.loads(out)
    return d.get('result', d.get('error'))
def call(to, sig, args_enc=''):
    import subprocess
    sel = subprocess.run(['cast','sig',sig],capture_output=True,text=True).stdout.strip()
    r = rpc('eth_call',[{'to':to,'data':sel+args_enc},'latest'])
    return r
VM='0x878bd0593dfc1ff302e3a20e98fc4f97cf516c15'
def u25(x): return int(x,0) if isinstance(x,str) else x
for fn in ['operatorRewardsMap(uint256)','daoRewardsMap(uint256)','unclaimedRewardsMap(uint256)']:
    for oid in range(0,8):
        r = call(VM, fn, '%064x'%oid)
        if isinstance(r,dict) or (r and r!='0x'+'0'*64):
            print(fn,oid,r)
