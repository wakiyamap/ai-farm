import json, urllib.request, os
RELAY=os.environ.get('RPC_RELAY_URL','http://127.0.0.1:8545')
EP=f"{RELAY}/base?lane=research"
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(EP, data=body, headers={"content-type":"application/json"})
    j=json.loads(urllib.request.urlopen(req, timeout=60).read())
    return j.get('result', j.get('error'))
def call(to, data, blk='latest'):
    return rpc('eth_call', [{'to':to,'data':data}, blk])
EURC='0x60a3e35Cc302BFA44cB288bc5A4f316FDb1aDb42'
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
M_EURC_BORROW='0xb682c840b5f4fc58b20769e691a6fa1305a501a2'
BOR='0x33a7ec1055edd4cc35ef289156c7a7a078043474'
SEL_BOF='0x70a08231'; SEL_DEC='0x313ce567'; SEL_CASH='0x3b1d21a2'
out={}
# 1. EURC decimals + Morpho pool via pool(address) selector variants
d=call(EURC, SEL_DEC); out['eurc_decimals']=int(d,16) if isinstance(d,str) else d
for selname,sel in (('pool(address)','0x156522a8'),):
    r=call(MORPHO, sel + EURC[2:].lower().rjust(64,'0'))
    out['morpho_'+selname]= r if not isinstance(r,str) else '0x'+r[-40:]
# if pool found, measure depth
p=out.get('morpho_pool(address)')
if isinstance(p,str) and int(p,16)!=0:
    out['eurc_balance_pool']=int(call(EURC, SEL_BOF+p[2:].lower().rjust(64,'0')),16)
# 2. mEURC borrow market cash at capture-1 (repay leg source? no - repay from flash; but borrow market cash matters for redemption? borrow market = mEURC: executor repays borrow; market cash irrelevant)
for cap in (55046981, 55076179, 55095244):
    out[f'cash_mEURC@{cap-1}']=int(call(M_EURC_BORROW, SEL_CASH, hex(cap-1)),16) if isinstance(call(M_EURC_BORROW,SEL_CASH,hex(cap-1)),str) else call(M_EURC_BORROW,SEL_CASH,hex(cap-1))
# 3. capture txs: from == liquidator? input length (loop?)
for h in ('0x0c90eba8ac18bbacf72fccdd530b944020033547b5b973fd42faffc430708845','0xadb81cb5a9674f9314203564228931ade2a857a75470696d1d6625e311e9ccc1','0xc86afdf0b83c424dec9ecadb5159b37fc37fa8de221cf208b347d0d1053f4f54'):
    t=rpc('eth_getTransactionByHash',[h])
    if isinstance(t,dict):
        out['tx_'+h[:10]]={'from':t['from'],'to':t['to'],'input_len':(len(t['input'])-2)//2,'fn':t['input'][:10]}
print(json.dumps(out,indent=1))
