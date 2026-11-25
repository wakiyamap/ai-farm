import json, urllib.request, os
RELAY=os.environ['RPC_RELAY_URL']; HEAD=26363073; PAGES=int(os.environ.get('PAGES','65')); PAGE=10000
POOL=os.environ.get('POOL','0xae05Cd22df81871bc7cC2a04BeCfb516bFe332C8')
TOPIC='0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
addr=POOL.lower(); out=[]
start=HEAD-PAGES*PAGE
for i in range(PAGES):
    f=start+i*PAGE+1; t=start+(i+1)*PAGE
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"address":[addr],"topics":[[TOPIC]],"fromBlock":hex(f),"toBlock":hex(t)}]}).encode()
    req=urllib.request.Request(f"{RELAY}/ethereum?lane=research",data=body,headers={'content-type':'application/json'})
    r=json.loads(urllib.request.urlopen(req,timeout=30).read())
    logs=r.get('result') or []
    if r.get('error'): print('ERR',r['error'],f,t); break
    for lg in logs: out.append({'block':int(lg['blockNumber'],16),'tx':lg['transactionHash'],'data':lg['data'],'topics':lg['topics']})
    print('.',end='',flush=True)
print()
print('events',len(out))
for e in out[:6]:
    d=e['data']; debt=int(d[64:128],16); reward=int(d[128:192],16)
    print(e['block'], e['tx'], 'debt_raw',debt,'reward_raw',reward,'collat',e['topics'][1][26:],'debtAsset',e['topics'][2][26:],'user',e['topics'][3][26:])
json.dump(out,open('scratch/horizon-events.json','w'))
