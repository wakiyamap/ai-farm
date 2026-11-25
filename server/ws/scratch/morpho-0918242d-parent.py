import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/srv/farm/ws')
sys.path.insert(0, str(ROOT / 'scratch/census-a33d'))
from hfcheck import state

q = "SELECT block,tx_hash,fields FROM (SELECT block,tx_hash,fields,ROW_NUMBER() OVER (PARTITION BY tx_hash ORDER BY log_index) AS rn FROM events WHERE chain='base' AND protocol='morpho_blue' AND actor='0x0918242d33718b7cb3a1c6dd36fdfa9e9db37786') WHERE rn=1 ORDER BY block DESC LIMIT 30"
p = subprocess.run(['ledger','query','--json',q], cwd=ROOT, capture_output=True, text=True, check=True)
events = [json.loads(line) for line in p.stdout.splitlines() if line.strip()]
by_tx = {}
for ev in events:
    by_tx.setdefault(ev['tx_hash'], ev)

out = []
for tx, ev in by_tx.items():
    f = json.loads(ev['fields'])
    item = {'tx_hash': tx, 'capture_block': ev['block'], 'market': f['id'], 'repaid_assets': f['repaidAssets']}
    try:
        item['parent'] = state({'f': f}, ev['block'] - 1)
        item['capture'] = state({'f': f}, ev['block'])
    except Exception as exc:
        item['error'] = str(exc)
    out.append(item)
    print(json.dumps(item), flush=True)

(ROOT / 'scratch/morpho-0918242d-parent.json').write_text(json.dumps(out, indent=2))
