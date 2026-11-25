import json, subprocess

def rpc(m,p):
 x=subprocess.run(['python3','tools/rpc.py','ethereum',m,json.dumps(p)],capture_output=True,text=True,check=True)
 j=json.loads(x.stdout)
 if 'error' in j: raise Exception(j['error'])
 return j['result']
markets=['0xf8ec0f87036565d6b2b19780a54996c3b03e91ea','0xe6ef65ec40d943c3f675165b0b17e06862fe3d82','0xdbdf2fc3af896e18f2a9dc58883d12484202b57e','0xf146c26136c1f80c9f0967d27bcb7e500d45681f','0x913f50d0195e92bb76c453d61b969dc5d20afa3d','0x9affb6d8568cefa2837d251b1553967430d1a5e5','0x7d4377114fd3c61c59d72de48102bf6acd3882b1','0x7ecc1d6fc7f63b003de4391dfd4c78365e844e1d','0x11581582aa816c8293e67c726af49fc2c8b98c6e','0xb9351dcd5347a67a1a2e0e72c1d069fb1f2e1d65','0x43647239ede197099b57bf72d0373f8049acfb0f','0x40340fdce2310fdea42589c4a9fe029f1ed80730','0x93f02045b350877f82abbb387bc3f8a05ecb8aab','0xada37514948649a61a3d6da30585aaef78d88fe3','0x97f84825d16b32ca97afc1c8bf51ab1086bcff1f','0xaef3f76e426d2f0139eaecd19672dd9c9a3fc582','0x8c83b281fa131360fc90a83397a3afa5c1d8e8a7','0xcdea28bb9e923ab33cbc5cf2652b98d700d8f988','0x43c97fceadd7dbb1cf1fab54bd8f467165a42461']
topic='0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'
start=26430672; end=26480914
for a in range(start,end+1,8000):
 for l in rpc('eth_getLogs',[{'address':markets,'topics':[topic],'fromBlock':hex(a),'toBlock':hex(min(a+7999,end))}]):
  d=l['data'][2:]; ws=[d[i:i+64] for i in range(0,len(d),64)]
  tx=rpc('eth_getTransactionByHash',[l['transactionHash']]); rec=rpc('eth_getTransactionReceipt',[l['transactionHash']]);
  print(json.dumps({'tx':l['transactionHash'],'block':int(l['blockNumber'],16),'market':l['address'],'liquidator':'0x'+ws[0][-40:],'borrower':'0x'+ws[1][-40:],'repay_raw':int(ws[2],16),'collateral':'0x'+ws[3][-40:],'seize_tokens_raw':int(ws[4],16),'tx_from':tx['from'],'tx_to':tx['to'],'gas_used':int(rec['gasUsed'],16),'effective_gas_price_wei':int(rec['effectiveGasPrice'],16)}),flush=True)
