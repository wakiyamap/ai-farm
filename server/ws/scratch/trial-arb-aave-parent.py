import concurrent.futures
import json
import subprocess

SQL = "SELECT block,tx_hash,json_extract(fields,'$.user') AS user,json_extract(fields,'$.collateralAsset') AS asset,CAST(json_extract(fields,'$.debtToCover') AS TEXT) AS cover,CAST(json_extract(fields,'$.liquidatedCollateralAmount') AS TEXT) AS seized FROM events WHERE chain='arbitrum' AND protocol='aave_v3' AND kind='liquidation' AND ts>=strftime('%s','now')-7*86400 AND json_extract(fields,'$.collateralAsset')=json_extract(fields,'$.debtAsset') ORDER BY block DESC LIMIT 50"
rows = [json.loads(x) for x in subprocess.check_output(['ledger', 'query', '--json', SQL], text=True).splitlines()]

def probe(row):
    data = '0xbf92857c' + row['user'][2:].lower().zfill(64)
    params = json.dumps([{'to': '0x794a61358d6845594f94dc1db02a252b5b4814ad', 'data': data}, hex(row['block'] - 1)])
    p = subprocess.run(['python3','tools/rpc.py','arbitrum','eth_call',params], capture_output=True, text=True, timeout=45)
    try:
        h = json.loads(p.stdout)['result']
        row['parent_hf'] = int(h[2+64*5:2+64*6], 16)/1e18
    except Exception:
        row['error'] = (p.stdout + p.stderr)[:300]
    return row

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    out = list(pool.map(probe, rows))
with open('scratch/trial-arb-aave-parent.json','w') as f:
    json.dump(out, f, indent=2)
print(json.dumps({'n':len(out),'ok':sum('parent_hf' in x for x in out),'parent_healthy':sum(x.get('parent_hf',0)>=1 for x in out),'parent_unhealthy':sum(0<x.get('parent_hf',0)<1 for x in out),'errors':[x for x in out if 'error' in x][:2]},indent=2))
