import json,urllib.request,os
url=os.environ['RPC_RELAY_URL']+'/optimism?lane=research'
def raw(m,p):
    req=urllib.request.Request(url,data=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=60).read())
head=int(raw('eth_blockNumber',[])['result'],16)
T0='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
CTRL='0x394a9fcbab8599437d9ec4e5a4a0eb7cb1fd2f69'
for rng,spec in [(10,{}),(10,{"topics":[T0]}),(200,{"topics":[T0]})]:
    r=raw('eth_getLogs',[{"address":CTRL,"fromBlock":hex(head-rng),"toBlock":hex(head)}|spec])
    print(rng, 'logs' if 'result' in r else 'ERR', len(r.get('result',[])) if 'result' in r else json.dumps(r.get('error'))[:100])
