import json, os, urllib.request
URL = os.environ.get('RPC_RELAY_URL','').rstrip('/') + '/hyperevm?lane=scout'
def call(method, params):
    req = urllib.request.Request(URL, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), headers={"Content-Type":"application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    if 'error' in r: return None
    return r['result']
def eth_call(to, data):
    r=call('eth_call',[{"to":to,"data":data},"latest"])
    return r
logs=json.load(open('scratch/hl_logs.json'))['liq']
ASSET='0x38d52e0f'; SYM='0x95d89b41'; DEC='0x313ce567'; CONV=bytes.fromhex('070003c7').hex()  # convertToAssets(uint256)? check
print('conv sig check:', CONV)
info={}
def assetinfo(vault):
    if vault in info: return info[vault]
    a=eth_call(vault,ASSET); a='0x'+a[-40:]
    sym=eth_call(vault,SYM)
    try:
        s=bytes.fromhex(sym[2:]); ln=int(s[64:128],16); name=s[128:128+ln].decode()
    except Exception: name='?'
    d=int(eth_call(vault,DEC),16)
    info[vault]=(a,name,d)
    return info[vault]
import subprocess
res=[]
for L in logs:
    dd=L['data'][2:]
    coll_vault='0x'+dd[24:64]; repay=int(dd[64:128],16); yb=int(dd[128:192],16)
    da,dn,ddc=assetinfo(L['address'])
    ca,cn,cdc=assetinfo(coll_vault)
    # convert seized shares -> assets on coll vault
    r=eth_call(coll_vault,'0x070003c7'+format(yb,'064x'))
    seized=int(r,16) if r else None
    res.append({'tx':L['transactionHash'],'blk':int(L['blockNumber'],16),'liq':'0x'+L['topics'][1][-40:],'debt_name':dn,'debt_dec':ddc,'repay':repay,'debt_asset':da,'coll_name':cn,'coll_dec':cdc,'seized_assets':seized,'coll_asset':ca})
print(json.dumps(res,indent=1))
# receipts
txs=sorted({L['transactionHash'] for L in logs})
for t in txs:
    r=call('eth_getTransactionReceipt',[t])
    print(t[:14], 'status',r['status'],'gasUsed',int(r['gasUsed'],16),'effGasPrice',int(r['effectiveGasPrice'],16),'base',int(call('eth_getBlockByNumber',[hex(int(r['blockNumber'],16)),False])['baseFeePerGas'],16))
