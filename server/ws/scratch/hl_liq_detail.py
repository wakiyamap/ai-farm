import json, os, urllib.request
URL = os.environ.get('RPC_RELAY_URL','').rstrip('/') + '/hyperevm?lane=scout'
def call(method, params):
    req = urllib.request.Request(URL, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), headers={"Content-Type":"application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    if 'error' in r: return None
    return r['result']
logs=json.load(open('scratch/hl_logs.json'))['liq']
seen_tx=set()
for L in logs:
    d=L['data'][2:]
    coll_vault='0x'+d[24:64]; repay=int(d[64:128],16); yb=int(d[128:192],16)
    liq='0x'+L['topics'][1][-40:]; viol='0x'+L['topics'][2][-40:]
    txh=L['transactionHash']
    if txh not in seen_tx:
        tx=call('eth_getTransactionByHash',[txh])
        sender=tx['from'] if tx else '?'
        seen_tx.add(txh)
    else:
        sender='(same tx)'
    # debt asset of the vault, collateral asset of coll_vault
    debt_asset=call('eth_call',[{"to":L['address'],"data":"0x38d52e0f"},"latest"])  # asset()
    debt_asset='0x'+debt_asset[-40:] if debt_asset else '?'
    coll_asset=call('eth_call',[{"to":coll_vault,"data":"0x38d8b4f0"},"latest"])  # asset()
    coll_asset='0x'+coll_asset[-40:] if coll_asset else '?'
    print(json.dumps({"tx":txh,"block":int(L['blockNumber'],16),"debt_vault":L['address'],"debt_asset":debt_asset,"repay_raw":repay,"coll_vault":coll_vault,"coll_asset":coll_asset,"yieldbal_raw":yb,"liquidator":liq,"violator":viol,"sender":sender}))
