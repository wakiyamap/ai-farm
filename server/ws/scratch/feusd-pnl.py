import datetime
import json
import pathlib
import subprocess

ROOT = pathlib.Path('/srv/farm/ws/scratch')
CUTOFF = int(datetime.datetime(2026, 11, 10, 5, 10, tzinfo=datetime.timezone.utc).timestamp())
TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
USDT = '0xb8ce59fc3717ada4c02eadf9682a9e934f625ebb'
OWNERS = {215: '6b78f49000fc7454d0e81681a8f3eda741994c50', 212: '18c6a0c85655824ab3000f8d7c1160da750c0b2e'}
SELECTORS = {215: '0x555312c0', 212: '0x9d410c42'}

def receipt(txhash):
    cp = subprocess.run(['python3', 'tools/rpc.py', 'hyperevm', 'eth_getTransactionReceipt', json.dumps([txhash])], cwd='/srv/farm/ws', text=True, capture_output=True)
    if cp.returncode:
        raise RuntimeError(cp.stderr)
    return json.loads(cp.stdout)['result']

out = []
for actor in (215, 212):
    for line in (ROOT / f'feusd-actor{actor}-txs.txt').read_text().splitlines():
        parts = line.split()
        if int(parts[1]) < CUTOFF or SELECTORS[actor] not in parts:
            continue
        r = receipt(parts[2])
        gross = sum(int(log['data'], 16) for log in r['logs'] if log['address'].lower() == USDT and log['topics'][0].lower() == TRANSFER and log['topics'][2][-40:].lower() == OWNERS[actor]) / 1e6
        gas = int(r['gasUsed'], 16) * int(r['effectiveGasPrice'], 16) / 1e18
        out.append({'actor': actor, 'tx': parts[2], 'block': int(parts[0]), 'ts': int(parts[1]), 'success': int(r['status'],16), 'gross_usdt': gross, 'gas_hype': gas, 'gas_used': int(r['gasUsed'],16)})
    print(actor, sum(x['actor'] == actor for x in out), flush=True)
(ROOT / 'feusd-pnl.json').write_text(json.dumps(out, indent=2))
for actor in (215,212):
    x = [r for r in out if r['actor'] == actor]
    gross = sum(r['gross_usdt'] for r in x)
    gas = sum(r['gas_hype'] for r in x)
    print(actor, 'calls', len(x), 'wins', sum(r['success'] for r in x), 'gross_usdt', round(gross,6), 'gas_hype', round(gas,8), 'gas_usd_at_68.75', round(gas*68.75,4), 'net_usd_68.75', round(gross-gas*68.75,4))
