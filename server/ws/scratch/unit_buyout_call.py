import json, subprocess
def rpc(method, params):
    out = subprocess.run(['python3','tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True).stdout
    r = json.loads(out)
    return r
# buyout(WETH, cdp owner) from fresh address
data = '0x16e78ac9'+'000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'+'000000000000000000000000c2a639c930a3e931171be1136ca400d2b5138324'
r = rpc('eth_call',[{'from':'0x1111111111111111111111111111111111111111','to':'0x9cCbb2F03184720Eef5f8fA768425AF06604Daf4','data':data},'latest'])
print('fresh buyout call:', r)
# last buyout receipt
r = rpc('eth_getTransactionReceipt',['0x40765bbcd5d29dcd9d5461bc5a6c47b999130800d03606751d794c1d6b09257c'])
rec = r['result']
if rec:
    print('status', rec['status'], 'gasUsed', int(rec['gasUsed'],16), 'block', int(rec['blockNumber'],16))
    for lg in rec['logs']:
        if lg['address'].lower()=='0x9ccbb2f03184720eef5f8fa768425af06604daf4':
            t=[x for x in lg['topics']]
            d=lg['data'][2:]
            print('topic0', t[0])
            print('asset', '0x'+t[1][-40:], 'owner', '0x'+t[2][-40:], 'buyer', '0x'+t[3][-40:])
            print('amount', int(d[0:64],16), 'price', int(d[64:128],16), 'penalty', int(d[128:192],16))
