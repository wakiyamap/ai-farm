import json, subprocess
M={'cbBTC':('0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836',1e8,58077.77,'0x663becd10dae6c4a3dcd89f1d76c1174199639b9'),
   'cbETH':('0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d',1e18,1650.94,'0x97ff9cbd7e77348b2b8ffbb883bf29452ad18295'),
   'cbXRP':('0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109',1e6,0.9014,'0x031b2efc8d70042ac8d9f5c793c4149ec4b60fde'),
   'JitoSOL':('0x09276541cfecb6920a80679a1deced4dde3ae64bf5fc2c9c1f9c21e0c152e1a5',1e9,68.64,'0x78f772f5fcc03256260cc1165e34da9bb3f9be1c')}
def rpc(method, params):
    p=subprocess.run(['python3','tools/rpc.py','base',method,json.dumps(params)],capture_output=True,text=True)
    if not p.stdout: return {'error':p.stderr.strip()}
    return json.loads(p.stdout)
def call(to,data,blk):
    r=rpc('eth_call',[{'to':to,'data':data},hex(blk) if isinstance(blk,int) else blk])
    return r.get('result')
# feeds per market
feeds={}
for k,(mid,d,p,orcl) in M.items():
    r=call(orcl,'0xf50a4718','latest')
    feeds[k]='0x'+r[-40:] if r and not r.get('error') if isinstance(r,str) else None
print('feeds',feeds)
