import json, subprocess

VAULT='0xa980d4c0C2E48d305b582AA439a3575e3de06f0E'
START=26430151
END=26480394
TOPIC='0xe64f87293a785dc4cbf1b9b65f3cfd04beb2bac2c656aec8f79b2e70be1f8873'
def rpc(method, params):
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True)
    x=json.loads(p.stdout)
    if p.returncode or 'error' in x: raise RuntimeError(x)
    return x['result']

POOL='0x2673099769201c08e9a5e63b25fbaf25541a6557'
logs=rpc('eth_getLogs',[{'address':VAULT,'fromBlock':hex(START),'toBlock':hex(END),'topics':[TOPIC]}])
events=[]
for x in logs:
    w=[int(x['data'][i:i+64],16) for i in range(2,len(x['data']),64)]
    events.append((w[0],w[1],x['transactionHash']))
for steth,pay,h in sorted(events,reverse=True)[:5]:
    data='0x07211ef7'+(0).to_bytes(32,'big').hex()+(2).to_bytes(32,'big').hex()+pay.to_bytes(32,'big').hex()
    usdc=int(rpc('eth_call',[{'to':POOL,'data':data},'latest']),16)
    print(h,steth,pay,usdc)
