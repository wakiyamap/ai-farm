import subprocess, json
def rpc(method, params=[]):
    r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','arbitrum',method,json.dumps(params)], capture_output=True, text=True)
    out = json.loads(r.stdout)
    if 'error' in out: return {'ERR': out['error']}
    return out['result']
WETH='0x82af49447d8a07e3bd95bd0d56f35241523fbab1'
for h in ['0x65e654cf172ba8a442d57aaf81f3f814f9fafe25eeaf4333f26d8e777fbcd7d8','0x9335b085863bc40febae4a5889d8dd69477f9f17521c8f21234ca7b1094134fa']:
    rc=rpc('eth_getTransactionReceipt',[h])
    if isinstance(rc,dict) and 'ERR' in rc: print(h[:12],rc); continue
    print(h[:12],'status',rc['status'],'gasUsed',int(rc['gasUsed'],16),'logs',len(rc['logs']))
    for lg in rc['logs']:
        if lg['address'].lower()==WETH:
            print('   WETH Transfer value:', int(lg['data'],16)/1e18)
