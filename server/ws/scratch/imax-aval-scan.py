import subprocess, json, sys

def rpc(method, params):
    r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','avalanche',method,
                        json.dumps(params)],capture_output=True,text=True)
    try:
        d = json.loads(r.stdout)
        if 'result' in d: return d['result']
        print("ERR", d.get('error'), str(params)[:120], file=sys.stderr)
        return None
    except Exception:
        print("BAD", r.stdout[:200], r.stderr[:120], file=sys.stderr)
        return None

pools = json.load(open('/srv/farm/ws/scratch/imax-aval-pools.json'))
borrowables = [p[k] for p in pools for k in ('borrowable0','borrowable1') if p[k] and int(p[k],16)]
collaterals = [p['collateral'] for p in pools if p['collateral'] and int(p['collateral'],16)]
print("borrowables", len(borrowables), "collaterals", len(collaterals))

FROM, TO = 100482316, 'latest'
LIQ = '0xb0dbe18c6ffdf0da655dd690e77211d379205c497be44c64447c3f5f021b5167'
BOR = '0x33f3048bd4e6af45e53afb722adfd57dbde82da7e93e44db921fb4b8c6a70c4b'
REI = '0xc003f45bc224d116b6d079100d4ab57a5b9633244c47a5a92a176c5b79a85f28'

def scan(addrs, topics, label):
    logs = []
    for i in range(0, len(addrs), 32):
        chunk = addrs[i:i+32]
        f = {'fromBlock': hex(FROM), 'toBlock': TO, 'address': chunk, 'topics': [topics]}
        res = rpc('eth_getLogs', [f])
        if res is None:
            print("SCAN FAIL", label, i); continue
        logs += res
    return logs

bl = scan(borrowables, [BOR, LIQ], 'borrow+liquidate')
rl = scan(collaterals, [REI], 'reinvest')
out = {'borrow_liquidate': bl, 'reinvest': rl}
json.dump(out, open('/srv/farm/ws/scratch/imax-aval-logs7d.json','w'))
nb = sum(1 for l in bl if l['topics'][0]==BOR); nl = sum(1 for l in bl if l['topics'][0]==LIQ)
print("7d: Borrow", nb, "Liquidate", nl, "Reinvest", len(rl))
for l in bl[:10]: print(l['blockNumber'], l['address'], l['topics'][0][:10], l['transactionHash'])
for l in rl[:10]: print(l['blockNumber'], l['address'], l['transactionHash'])
