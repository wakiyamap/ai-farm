import json
import subprocess
from pathlib import Path

rows = [json.loads(x) for x in Path('scratch/aave-balancer-events.jsonl').read_text().splitlines()]
owner = '0x' + 'e496925f46554b086eeb45c832f7727cb58c4602'.rjust(64, '0')
transfer = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
out = []
for row in rows:
    cmd = ['python3', 'tools/rpc.py', 'arbitrum', 'eth_getTransactionReceipt', json.dumps([row['tx_hash']])]
    receipt = json.loads(subprocess.check_output(cmd, text=True))['result']
    payouts = []
    for log in receipt['logs']:
        if (len(log['topics']) >= 3 and log['topics'][0] == transfer
                and log['topics'][2].lower() == owner.lower()):
            payouts.append({'token': log['address'], 'raw': int(log['data'], 16)})
    out.append({'tx': row['tx_hash'], 'block': row['block'], 'gas_used': int(receipt['gasUsed'], 16),
                'gas_wei': int(receipt['gasUsed'], 16) * int(receipt['effectiveGasPrice'], 16),
                'payouts': payouts})
Path('scratch/aave-balancer-economics.json').write_text(json.dumps(out, indent=2) + '\n')
for x in out:
    print(x['tx'], x['gas_used'], x['gas_wei'], x['payouts'])
