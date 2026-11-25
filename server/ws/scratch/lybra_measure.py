import json, subprocess, collections, datetime

VAULT='0xa980d4c0C2E48d305b582AA439a3575e3de06f0E'
START=26430151
END=26480394
TOPICS=['0xe64f87293a785dc4cbf1b9b65f3cfd04beb2bac2c656aec8f79b2e70be1f8873','0xb59dc9737d55b75fc6ca7522e82d6161da5d7c8337b9ab990a5846f95b5ccdad','0xec0804e8e1decb589af9c4ba8ebfbacd3be98929d4d53457dfd186061f489f04']
def rpc(method, params):
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True)
    x=json.loads(p.stdout)
    if p.returncode or 'error' in x: raise RuntimeError(x)
    return x['result']
logs=rpc('eth_getLogs',[{'address':VAULT,'fromBlock':hex(START),'toBlock':hex(END),'topics':[TOPICS]}])
print('window',START,END,'events',dict(collections.Counter(x['topics'][0] for x in logs)))
txs=sorted(set(x['transactionHash'] for x in logs))
for h in txs:
    tx=rpc('eth_getTransactionByHash',[h]); receipt=rpc('eth_getTransactionReceipt',[h])
    event=[x for x in logs if x['transactionHash']==h]
    cap=next((x for x in event if x['topics'][0]==TOPICS[0]),None)
    liq=next((x for x in event if x['topics'][0]==TOPICS[1]),None)
    words=lambda x:[int(x[i:i+64],16) for i in range(2,len(x),64)]
    print(json.dumps({'hash':h,'block':int(tx['blockNumber'],16),'from':tx['from'],'to':tx['to'],'input':tx['input'][:10],
        'gas_used':int(receipt['gasUsed'],16),'gas_price_gwei':int(receipt['effectiveGasPrice'],16)/1e9,
        'cap_words':words(cap['data']) if cap else None,'liq_words':words(liq['data']) if liq else None,
        'liq_topics':liq['topics'] if liq else None}))
