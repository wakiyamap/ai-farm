import subprocess, json
def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True).stdout
    return json.loads(out)
VM='0x878bd0593dfc1ff302e3a20e98fc4f97cf516c15'
FRESH='0x1111111111111111111111111111111111111111'
def sel(sig): return subprocess.run(['cast','sig',sig],capture_output=True,text=True).stdout.strip()
def enc_uints(xs): 
    out=''; off=32; body=''
    body+='%064x'%len(xs)
    for x in xs: body+='%064x'%x
    return ('%064x'%off)+body
tests=[
 ('claimRewardsOfDao(uint256[])', enc_uints([0])),
 ('claimRewardsOfDao(uint256[])', enc_uints([0,1,2,3,4,5,6,7])),
 ('claimRewardsOfOperator(uint256)', '%064x'%0),
 ('claimRewardsOfUser(uint256[])', enc_uints([1])),
 ('settleAndReinvestElReward(uint256[])', enc_uints([0])),
]
for sig,enc in tests:
    r=rpc('eth_call',[{'from':FRESH,'to':VM,'data':sel(sig)+enc},'latest'])
    if 'error' in r: print(sig, '-> REVERT', r['error'].get('message'), r['error'].get('data','')[:20])
    else: print(sig, '-> OK, returns', r['result'][:66])
