import json,urllib.request,os
RELAY=os.environ.get('RPC_RELAY_URL','http://127.0.0.1:8545')
def call(chain,lane,method,params):
    req=urllib.request.request if False else None
    data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    with urllib.request.urlopen(f"{RELAY}/{chain}?lane={lane}",data,timeout=60) as r:
        d=json.loads(r.read())
    if 'error' in d: raise RuntimeError(json.dumps(d['error'])[:300])
    return d['result']
wallets=["0x03a7e58745874d49b3acc770c40261a3ce206608","0xc2a290eceac480f057b6e7b45a7a949535e478ce","0xdc379823a9a3a2ca9d77c33299551ecdbabf7a41","0x91ba525861c16aa8cd4d6974e4058cc846f42ebe"]
latest=call('arbitrum','research','eth_blockNumber',[])
start=hex(int(latest,16)-20000)
out={}
for i,w in enumerate(wallets):
    p=[{"fromBlock":start,"toBlock":"latest","to":w,"maxCount":"0x32","tokens":[],"assetTransfers":False,"excludeFailedTxs":False,"includeTransfers":True,"kind":["erc20","ether"]}]
    try:
        r=call('arbitrum','research','alchemy_getAssetTransfers',p)
        out[w]=[{"from":t["from"],"to":t["to"],"asset":t.get("asset") or t.get("rawContract") and t["rawContract"].get("asset") or t["rawContract"].get("currencyService") or t["rawContract"].get("erc20") or t["rawContract"].get("token") , "gas":t.get("gas")} for t in r.get("transfers",[])[:60]]
    except Exception as e:
        out[w]=str(e)[:200]
json.dump(out,open('scratch/azx-transfers.json','w'),indent=1)
print(json.dumps(out,indent=1)[:3000])
