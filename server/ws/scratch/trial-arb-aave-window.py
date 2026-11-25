import concurrent.futures
import json
import subprocess

rows = [x for x in json.load(open('scratch/trial-arb-aave-parent.json')) if x['parent_hf'] < 1]
offsets = [2, 4, 8, 16, 32, 64, 128, 256, 1024]
jobs = [(i,o) for i in range(len(rows)) for o in offsets]

def probe(job):
    i,o = job
    row = rows[i]
    data = '0xbf92857c' + row['user'][2:].lower().zfill(64)
    params = json.dumps([{'to': '0x794a61358d6845594f94dc1db02a252b5b4814ad', 'data': data}, hex(row['block'] - o)])
    p = subprocess.run(['python3','tools/rpc.py','arbitrum','eth_call',params], capture_output=True, text=True, timeout=45)
    try:
        h = json.loads(p.stdout)['result']
        return i,o,int(h[2+64*5:2+64*6],16)/1e18
    except Exception:
        return i,o,(p.stdout+p.stderr)[:100]

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for i,o,v in pool.map(probe,jobs):
        rows[i][str(o)] = v
with open('scratch/trial-arb-aave-window.json','w') as f:
    json.dump(rows,f,indent=2)
for x in rows:
    print(x['block'],x['asset'][:10],x['cover'],round(x['parent_hf'],8),' '.join(f'{o}:{round(x[str(o)],8) if isinstance(x[str(o)],float) else x[str(o)]}' for o in offsets))
