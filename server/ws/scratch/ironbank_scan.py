import json, subprocess, sys

CHAIN = 'ethereum'
CORE = '0xAB1c342C7bf5Ec5F02ADEA1c2270670bCa144CbB'
TOPIC = '0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'

def rpc(method, params):
    p = subprocess.run(['python3', 'tools/rpc.py', CHAIN, method, json.dumps(params)], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f'{method}: {p.stderr[:250]} {p.stdout[:250]}')
    obj = json.loads(p.stdout)
    if 'error' in obj:
        raise RuntimeError(str(obj['error']))
    return obj['result']

head = rpc('eth_getBlockByNumber', ['latest', False])
end = int(head['number'], 16)
target = int(head['timestamp'], 16) - 604800
lo, hi = end - 52000, end - 49000
while hi - lo > 1:
    mid = (lo + hi) // 2
    ts = int(rpc('eth_getBlockByNumber', [hex(mid), False])['timestamp'], 16)
    if ts < target: lo = mid
    else: hi = mid
start_block = rpc('eth_getBlockByNumber', [hex(hi), False])
print(json.dumps({'window': {'start_block': hi, 'start_time': int(start_block['timestamp'],16), 'end_block':end, 'end_time':int(head['timestamp'],16)}}), flush=True)

data = rpc('eth_call', [{'to': CORE, 'data':'0xb0772d0b'}, 'latest'])
words = [data[i:i+64] for i in range(2,len(data),64)]
count = int(words[1],16)
markets = ['0x'+x[-40:] for x in words[2:2+count]]
print(json.dumps({'market_count': count, 'markets':markets}), flush=True)
all_liqs=[]
all_logs=[]
for a in range(hi, end+1, 2000):
    b = min(a+1999,end)
    filt={'address':markets,'fromBlock':hex(a),'toBlock':hex(b),'topics':[TOPIC]}
    liqs=rpc('eth_getLogs',[filt])
    all_liqs.extend(liqs)
    filt.pop('topics')
    logs=rpc('eth_getLogs',[filt])
    all_logs.extend(logs)
    print(json.dumps({'page':[a,b],'liqs':len(liqs),'all':len(logs)}),flush=True)
print(json.dumps({'result':{'liquidations_count':len(all_liqs),'all_logs_count':len(all_logs),'liquidations':all_liqs[:20], 'log_samples':all_logs[:5]}}),flush=True)
