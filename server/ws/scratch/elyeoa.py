import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def rpc(m,p=None):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p or []}).encode()
    req=urllib.request.Request(f"{URL}/elysium?lane={LANE}",b,{"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req,timeout=90).read())
    if 'error' in r: print(m, r['error']); return None
    return r["result"]
head=int(rpc("eth_blockNumber"),16)
res=rpc("alchemy_getAssetTransfers",[{
 "fromBlock":hex(head-30000),"toBlock":hex(head),
 "fromAddress":"0xf70da97812cb96acdf810712aa562db8dfa3dbef",
 "category":["external"],"maxCount":"0x5","withToken":True}])
txs=set()
for t in (res['transfers'] if res else []):
    print(t['toAddress'], t['assetDetails']['symbol'] if t.get('assetDetails') else '-', (t.get('rawContract') or {}).get('input','')[:10], t['transactionHash'][:14])
    txs.add(t['transactionHash'])
for h in list(txs)[:3]:
    tx=rpc("eth_getTransactionByHash",[h])
    print("TX", tx['to'], "input len", (len(tx['input'])-10)//2, "sel", tx['input'][:10], "value", tx['value'])
