import json,urllib.request,os
url=os.environ['RPC_RELAY_URL']
def rpc(method,params,lane='research'):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    r=urllib.request.urlopen(url.rstrip('/')+'/ethereum?lane='+lane, body, timeout=90)
    return json.load(r)
T0='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
FB='0x000000000000000000000000c59b0e4de5f1248c1140964e0ff287b192407e0c'
def scan(a,b,tag):
    r=rpc('eth_getLogs',[{"topics":[T0,FB],"fromBlock":hex(a),"toBlock":hex(b)}])
    if isinstance(r.get('error'),dict):
        print(tag,'ERR',r['error'].get('message')); return
    logs=r.get('result') or []
    print(tag,len(logs),'logs')
    if logs:
        print('  first blk',hex(int(logs[0]['blockNumber'],16)),'last blk',hex(int(logs[-1]['blockNumber'],16)))
scan(10240000,10540000,'control 2020 outflow')
scan(26109933,26369933,'recent 30d outflow')
