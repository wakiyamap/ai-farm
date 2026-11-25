import subprocess, json, sys

def call(to, data):
    r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','avalanche','eth_call',
                        json.dumps([{"to":to,"data":data},"latest"])],capture_output=True,text=True)
    try:
        d = json.loads(r.stdout)
        if 'result' in d: return d['result']
        print("ERR", to, data[:10], d.get('error'), file=sys.stderr)
        return None
    except Exception:
        print("BAD", to, data[:10], r.stdout[:150], r.stderr[:100], file=sys.stderr)
        return None

def word(res, i):  # 32-byte word i as hex address
    if not res or len(res) < 2+64*(i+1): return None
    return '0x'+res[2+64*i+24:2+64*(i+1)]

SEL_POOL = subprocess.run(['cast','sig','allLendingPools(uint256)'],capture_output=True,text=True).stdout.strip()
SEL_GLP  = subprocess.run(['cast','sig','getLendingPool(address)'],capture_output=True,text=True).stdout.strip()
print("selectors", SEL_POOL, SEL_GLP, file=sys.stderr)

factories = ['0x8C3736e2FE63cc2cD89Ee228D9dBcAb6CE5B767B',
             '0x9708e0b216a88d38d469b255ce78c1369ad898e6',
             '0xc7f24fd6329738320883ba429C6C8133e6492739']
pools = []
for f in factories:
    n = int(call(f, '0x714c0206'), 16)
    for i in range(n):
        pair = word(call(f, SEL_POOL + '%064x' % i), 0)
        pools.append((f, pair))
print("pairs:", len(pools), file=sys.stderr)

out = []
for f, pair in pools:
    res = call(f, SEL_GLP + pair[2:].lower().rjust(64,'0'))
    coll, b0, b1 = word(res,2), word(res,3), word(res,4)
    out.append({'factory':f,'pair':pair,'collateral':coll,'borrowable0':b0,'borrowable1':b1})
json.dump(out, open('/srv/farm/ws/scratch/imax-aval-pools.json','w'), indent=1)
print(json.dumps({'n':len(out),'sample':out[:3]}))
