import json,subprocess,statistics
x=json.load(open('scratch/keep3r-work-7d.json'))['result']
by_pay=sorted(x,key=lambda e:int(e['data'][2:66],16),reverse=True)
by_block=sorted(x,key=lambda e:int(e['blockNumber'],16))
samples=by_pay[:5]+[by_block[i] for i in [0,15,31,47,63] if by_block[i]['transactionHash'] not in {e['transactionHash'] for e in by_pay[:5]}]
for e in samples:
 h=e['transactionHash']
 def rpc(method):
  p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps([h])],capture_output=True,text=True)
  return json.loads(p.stdout)['result']
 tx=rpc('eth_getTransactionByHash'); rc=rpc('eth_getTransactionReceipt')
 print(json.dumps({'tx':h,'block':int(e['blockNumber'],16),'keeper':'0x'+e['topics'][3][-40:],'payment_kp3r':int(e['data'][2:66],16)/1e18,'gas_used':int(rc['gasUsed'],16),'gas_price_gwei':int(rc['effectiveGasPrice'],16)/1e9,'gas_eth':int(rc['gasUsed'],16)*int(rc['effectiveGasPrice'],16)/1e18,'to':tx['to'],'input':tx['input'],'status':rc['status']}))
