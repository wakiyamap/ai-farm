import subprocess, json, sys

def rpc(method, params, tries=3):
    for _ in range(tries):
        r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','avalanche',method,
                            json.dumps(params)],capture_output=True,text=True)
        try:
            d = json.loads(r.stdout)
            if 'result' in d: return d['result']
            sys.stderr.write("ERR "+str(d.get('error'))[:160]+"\n")
        except Exception:
            sys.stderr.write("BAD "+r.stdout[:160]+"\n")
    return None

pools = json.load(open('/srv/farm/ws/scratch/imax-aval-pools.json'))
borrowables = set(p[k].lower() for p in pools for k in ('borrowable0','borrowable1') if p[k] and int(p[k],16))
collaterals = set(p['collateral'].lower() for p in pools if p['collateral'] and int(p['collateral'],16))

FROM = 100482316
head = int(rpc('eth_blockNumber',[]),16)
LIQ = '0xb0dbe18c6ffdf0da655dd690e77211d379205c497be44c64447c3f5f021b5167'
BOR = '0x33f3048bd4e6af45e53afb722adfd57dbde82da7e93e44db921fb4b8c6a70c4b'
REI = '0xc003f45bc224d116b6d079100d4ab57a5b9633244c47a5a92a176c5b79a85f28'

logs = []
failed = 0
s = FROM
while s <= head:
    e = min(s+9999, head)
    res = rpc('eth_getLogs',[{'fromBlock':hex(s),'toBlock':hex(e),'topics':[[BOR,LIQ,REI]]}])
    if res is None:
        failed += 1
    else:
        logs += res
    s = e+1
print("head",head,"chunks failed",failed,"logs",len(logs))
mine = [l for l in logs if l['address'].lower() in borrowables|collaterals]
print("emitters in impermax set:", len(mine))
bytopic = {}
for l in mine:
    t = {BOR:'Borrow',LIQ:'Liquidate',REI:'Reinvest'}[l['topics'][0]]
    bytopic.setdefault(t,[]).append(l)
other = {}
for l in logs:
    if l['address'].lower() not in borrowables|collaterals:
        other.setdefault((l['address'].lower(),l['topics'][0][:10]),0)
        other[(l['address'].lower(),l['topics'][0][:10])]+=1
json.dump({'mine':mine,'other':other}, open('/srv/farm/ws/scratch/imax-aval-scan2.json','w'))
for t,v in bytopic.items():
    print(t, len(v))
    for l in v[:10]: print('  ',int(l['blockNumber'],16), l['address'], l['transactionHash'])
print("non-impermax emitters:", other)
