import subprocess, json

def rpc(method, params):
    r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','avalanche',method,
                        json.dumps(params)],capture_output=True,text=True)
    return json.loads(r.stdout)['result']

def call(to, data):
    res = rpc('eth_call',[{"to":to,"data":data},"latest"])
    return res

LIQ = '0xb0dbe18c6ffdf0da655dd690e77211d379205c497be44c64447c3f5f021b5167'
B = '0xb50b9f18e1f4644db60a2a4ad0bbefcc38b9f316'
SEL_U = subprocess.run(['cast','sig','underlying()'],capture_output=True,text=True).stdout.strip()
SEL_P = subprocess.run(['cast','sig','pair()'],capture_output=True,text=True).stdout.strip()
SEL_NAME = subprocess.run(['cast','sig','name()'],capture_output=True,text=True).stdout.strip()

u = call(B, SEL_U); print("underlying:", '0x'+u[-40:])
try:
    p = call(B, SEL_P); print("pair:", '0x'+p[-40:] if p and len(p)>=64 else p)
except Exception: print("pair(): n/a")
try:
    n = call(B, SEL_NAME)
    if n and len(n)>10:
        ln=int(n[66:],16)*2; print("borrowable name:", bytes.fromhex(n[66:66+ln]).decode(errors='replace'))
except Exception: print("name(): n/a")

for h in ['0xb397a4e802d4f18a2aac2dfad7c32099899ee784ea3788bed82097b875b1380f','0x9ba7b9ff686cdfdc9827ca4f28fbc42d459da78537d67c120f2c0978c307366d']:
    rc = rpc('eth_getTransactionReceipt',[h])
    print('---', h[:12])
    print('from', rc['from'], 'to', rc['to'], 'gasUsed', int(rc['gasUsed'],16), 'gasPrice', int(rc['effectiveGasPrice'],16))
    for l in rc['logs']:
        t0 = l['topics'][0]
        if t0 == LIQ:
            d = l['data']
            seize = int(d[2:66],16); repay = int(d[66:130],16)
            print('LIQUIDATE addr', l['address'], 'topics[1..3]:', [x[-40:] for x in l['topics'][1:]], 'seizeTokens', seize, 'repayAmount', repay)
        if t0 == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
            frm = l['topics'][1][-40:]; to = l['topics'][2][-40:]; amt = int(l['data'],16)
            print('  Transfer tok 0x%s: 0x%s -> 0x%s  %d' % (l['address'][-40:], frm, to, amt))
