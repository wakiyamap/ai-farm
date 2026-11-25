import json,urllib.request,os
url=os.environ['RPC_RELAY_URL']+'/optimism?lane=research'
def raw(m,p):
    req=urllib.request.Request(url,data=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=60).read())
def h(m,p): return raw(m,p)['result']
head=int(h('eth_blockNumber',[]),16)
T0='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
P='0x585af0b397ac42dbef7f18395426bf878634f18d'
# positive control first: same-shape scan on a known-active Uni v3 pool
CTRL='0x394a9fcbab8599437d9ec4e5a4a0eb7cb1fd2f69'
for name,A in [('pool0(velo factory)',P),('ctrl:Uni v3 hot pool',CTRL)]:
    r=raw('eth_getLogs',[{"address":A,"topics":[T0],"fromBlock":hex(head-2000),"toBlock":hex(head)}])
    if 'result' in r:
        logs=r['result']; print(name,len(logs),'Transfer logs in 2000 blocks')
    else: print(name,'ERR',json.dumps(r.get('error'))[:120])
