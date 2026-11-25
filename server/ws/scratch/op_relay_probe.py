import json,urllib.request,os,datetime
url=os.environ['RPC_RELAY_URL']+'/optimism?lane=research'
def raw(m,p):
    req=urllib.request.Request(url,data=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),headers={'content-type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=60).read())
head=int(raw('eth_blockNumber',[])['result'],16)
T0='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
CTRL='0x394a9fcbab8599437d9ec4e5a4a0eb7cb1fd2f69'  # Uni v3 pool, active in head-5 raw scan
TOK='0x0b2c639c533813f4aa9d7837caf62653d097ff85'   # busy token emitter in same window
out={'chain':'optimism','lane':'research','utc':str(datetime.datetime.utcnow()),'head':head,'tests':{}}
tests=[
 ('addr+topics pool 10blk',{"address":CTRL,"topics":[T0],"fromBlock":hex(head-10),"toBlock":hex(head)}),
 ('addr+topics token 10blk',{"address":TOK,"topics":[T0],"fromBlock":hex(head-10),"toBlock":hex(head)}),
 ('topic-only T0 10blk',{"topics":[T0],"fromBlock":hex(head-10),"toBlock":hex(head)}),
 ('addr-only pool 10blk',{"address":CTRL,"fromBlock":hex(head-10),"toBlock":hex(head)}),
]
for name,p in tests:
    r=raw('eth_getLogs',[p])
    out['tests'][name]= ('ERR:'+json.dumps(r.get('error'))[:90]) if 'result' not in r else len(r['result'])
    print(name,out['tests'][name])
json.dump(out,open('scratch/op-relay-probe.json','w'),indent=1)
