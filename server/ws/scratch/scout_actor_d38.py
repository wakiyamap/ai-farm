import json, subprocess
A='0xd38a5a7c3cec073884be9561b12d327236bde02f'
E='0x1b8e94763019968d1a3b8d586c5ef96d8ac3a9f6'
H=['0xe99db0985005ead7b95e31c96604bf5979cc87015fab3c4935e8b2c39b4061c7','0x2b49c3a6b8017d5c1b2f54aecdd748ea17820a2baac2fb8cb9f29c014ad598df','0x7bca4338916e02b73b753603fb65d1ff2b021a3b224527b66e7b6ec7cf0f85e2']
def rpc(method, params):
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','hyperevm',method,json.dumps(params)],capture_output=True,text=True)
    if p.returncode: return {'error':p.stderr+p.stdout}
    return json.loads(p.stdout)['result']
for h in H:
    tx=rpc('eth_getTransactionByHash',[h])
    r=rpc('eth_getTransactionReceipt',[h])
    b=int(r['blockNumber'],16)
    before=rpc('eth_getBalance',[A,hex(b-1)])
    after=rpc('eth_getBalance',[A,hex(b)])
    transfers=[]
    for l in r['logs']:
        if l['topics'][0]=='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef' and len(l['topics'])==3:
            fr='0x'+l['topics'][1][-40:]; to='0x'+l['topics'][2][-40:]
            if fr.lower() in (A,E) or to.lower() in (A,E): transfers.append((l['address'],fr,to,int(l['data'],16)))
    print(json.dumps({'hash':h,'block':b,'selector':tx['input'][:10],'gas':int(r['gasUsed'],16),'gasPrice':int(r['effectiveGasPrice'],16),'gasHype':int(r['gasUsed'],16)*int(r['effectiveGasPrice'],16)/1e18,'balanceDeltaHype':(int(after,16)-int(before,16))/1e18,'transfers':transfers}))
