import json, os, urllib.request
URL = os.environ.get('RPC_RELAY_URL','').rstrip('/') + '/hyperevm?lane=scout'
def call(method, params):
    req = urllib.request.Request(URL, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), headers={"Content-Type":"application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    if 'error' in r: return None
    return r['result']
def llama(ts, coins):
    url=f"https://coins.llama.fi/prices/historical/{ts}/{'%2C'.join(coins) if False else ','.join(coins)}"
    return json.load(urllib.request.urlopen(url, timeout=60))['coins']
logs=json.load(open('scratch/hl_logs.json'))['liq']
PRICES={ '0xb8ce59fc3717ada4c02eadf9682a9e934f625ebb':'USDT0','0xb88339cb7199b77e23db6e890353e22632ba630f':'USDC','0x5555555555555555555555555555555555555555':'WHYPE','0xfd739d4e423301ce9385c1fb8850539d657c296d':'kHYPE','0x9fdbda0a5e284c32744d2f17ee5c74b284993463':'UBTC','0xd8fc8f0b03eba61f64d08b0bef69d80916e5dda9':'beHYPE','0xac962fa04bf91b7fd0dc0c5c32414e0ce3c51e03':'?0xac962f'}
DEC={ '0xb8ce59fc3717ada4c02eadf9682a9e934f625ebb':6,'0xb88339cb7199b77e23db6e890353e22632ba630f':6,'0x5555555555555555555555555555555555555555':18,'0xfd739d4e423301ce9385c1fb8850539d657c296d':18,'0x9fdbda0a5e284c32744d2f17ee5c74b284993463':8,'0xd8fc8f0b03eba61f64d08b0bef69d80916e5dda9':18,'0xac962fa04bf91b7fd0dc0c5c32414e0ce3c51e03':18}
out=[]
for L in logs:
    dd=L['data'][2:]
    coll_vault='0x'+dd[24:64]; repay=int(dd[64:128],16); yb=int(dd[128:192],16)
    blk=int(L['blockNumber'],16)
    debt_asset='0x'+call('eth_call',[{"to":L['address'],"data":"0x38d52e0f"},"latest"])[-40:]
    # seized assets at historical block
    r=call('eth_call',[{"to":coll_vault,"data":"0x07a2d13a"+format(yb,'064x')},hex(blk)])
    seized=int(r,16) if r else 0
    ts=call('eth_getBlockByNumber',[hex(blk),False])
    tsi=int(ts['timestamp'],16) if isinstance(ts.get('timestamp'),str) else ts['timestamp']
    coll_asset='0x'+call('eth_call',[{"to":coll_vault,"data":"0x38d52e0f"},"latest"])[-40:]
    out.append({'tx':L['transactionHash'][:14],'blk':blk,'ts':tsi,'debt_asset':debt_asset,'repay':repay,'coll_asset':coll_asset,'seized':seized})
# historical prices for all assets at each ts
allc=set()
for o in out: allc|={o['debt_asset'],o['coll_asset']}
prices={}
for o in out:
    key=o['ts']
    if key not in prices:
        coins=[f"hyperevm:{a}" for a in allc]
        prices[key]=llama(key, coins)
for o in out:
    p=prices[o['ts']]
    da=p.get('hyperevm:'+o['debt_asset']); ca=p.get('hyperevm:'+o['coll_asset'])
    ru=o['repay']/10**DEC[o['debt_asset']]*da['price'] if da else None
    su=o['seized']/10**DEC[o['coll_asset']]*ca['price'] if ca else None
    o['repay_usd']=round(ru,3) if ru is not None else None
    o['seized_usd']=round(su,3) if su is not None else None
    o['gross_usd']=round(su-ru,3) if (su is not None and ru is not None) else None
    o['debt_sym']=da['symbol'] if da else '?'; o['coll_sym']=ca['symbol'] if ca else '?'
json.dump(out, open('scratch/hl_pnl.json','w'), indent=1)
for o in out: print(o['tx'], o['blk'], o['debt_sym'], o['repay_usd'], '|', o['coll_sym'], o['seized_usd'], '| gross', o['gross_usd'])
