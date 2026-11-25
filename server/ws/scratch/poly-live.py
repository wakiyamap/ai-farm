import json,os,urllib.request
URL=os.environ['RPC_RELAY_URL']
def rpc(method,params):
    data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode()
    r=urllib.request.urlopen(urllib.request.Request(f'{URL}/polygon?lane=research',data=data,headers={'content-type':'application/json'}),timeout=60)
    b=json.loads(r.read().decode())
    return b.get('result') if 'result' in b else b
MB="0x1bF0c2541F820E775182832f06c0B7Fc27A25f67"
head=int(rpc('eth_blockNumber',[]),16)
code=rpc('eth_getCode',[MB,'latest'])
print('code len', len(code) if isinstance(code,str) else code)
logs=rpc('eth_getLogs',[{'address':MB,'fromBlock':hex(head-4999),'toBlock':hex(head)}])
print('logs from MorphoBlue 5000 blocks:', len(logs) if isinstance(logs,list) else logs, logs[:3] if isinstance(logs,list) else '')
