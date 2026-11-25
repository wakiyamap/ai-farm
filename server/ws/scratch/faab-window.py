"""Binary search first takeable parent state for four faab09c4 captures."""
import json
import subprocess
from pathlib import Path

ROOT = Path('/srv/farm/ws')
CASES = json.loads((ROOT/'scratch/faab-parent-probe.json').read_text())
CASES = [CASES[i] for i in (0,3,6,9)]
RPC = '/srv/farm/ws/tools/rpc.py'
rows = []

def rpc(method, params):
    p = subprocess.run(['python3', RPC, 'base', method, json.dumps(params)], cwd=ROOT, text=True, capture_output=True)
    if not p.stdout:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)

for case in CASES:
    capture = case['capture_block']
    tx = case['request'][0]
    lo = capture-16  # healthy
    hi = capture-2   # liquidatable
    samples = []
    while hi-lo > 1:
        mid = (hi+lo)//2
        j = rpc('eth_call', [tx, hex(mid)])
        msg = j.get('error', {}).get('message', '')
        samples.append({'block':mid,'response':j})
        if 'position is healthy' in msg:
            lo = mid
        elif 'transferFrom reverted' in msg:
            hi = mid
        else:
            raise RuntimeError((mid, j))
    b0 = rpc('eth_getBlockByNumber', [hex(lo), False])['result']
    b1 = rpc('eth_getBlockByNumber', [hex(hi), False])['result']
    bc = rpc('eth_getBlockByNumber', [hex(capture), False])['result']
    row = {'capture_block':capture,'txhash':case['txhash'],'borrower':case['borrower'],
           'last_healthy_block':lo,'first_takeable_state_block':hi,
           'capture_timestamp':int(bc['timestamp'],16),'first_takeable_timestamp':int(b1['timestamp'],16),
           'last_healthy_timestamp':int(b0['timestamp'],16),
           'seconds_to_capture':int(bc['timestamp'],16)-int(b1['timestamp'],16),
           'blocks_to_capture':capture-hi,'samples':samples}
    rows.append(row)
    print(capture, 'first takeable state', hi, 'capture', capture, 'seconds', row['seconds_to_capture'], flush=True)

out=ROOT/'scratch/faab-window.json'
out.write_text(json.dumps(rows,indent=2)+'\n')
print(out)
