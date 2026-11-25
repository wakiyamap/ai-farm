import json, os, urllib.request

base = os.environ['RPC_RELAY_URL'].rstrip('/') + '/base?lane=paper'
holder = '0x0efb3150b0626041fd06f636cd27911b87d1b95a'
comp = '0xfbb21d0380bee3312b33c4353c8936a0f13ef26c'
data = '0x5ec88c79' + holder[2:].rjust(64, '0')
for block in [55297670, 55297676, 55297681, 55297682]:
    body = json.dumps({'jsonrpc':'2.0','id':1,'method':'eth_call','params':[{'to':comp,'data':data},hex(block)]}).encode()
    req = urllib.request.Request(base, data=body, headers={'content-type':'application/json'})
    reply = json.load(urllib.request.urlopen(req,timeout=30))
    raw = reply.get('result')
    if not raw:
        print(block, reply.get('error'))
        continue
    words = [int(raw[2+i*64:2+(i+1)*64],16) for i in range(3)]
    print(block, {'error':words[0], 'liquidity_usd':words[1]/1e18, 'shortfall_usd':words[2]/1e18})
