import json
import subprocess
from pathlib import Path

root = Path('/srv/farm/ws')
logs = [json.loads(x) for x in (root / 'bots/live/trial-flatmoney-arbitrum/logs/bot.jsonl').read_text().splitlines()]
opps = [x for x in logs if x.get('ev') == 'opportunity']
sends = [x for x in logs if x.get('ev') == 'send_result']
assert len(opps) == len(sends) == 13


def rpc(method, params):
    p = subprocess.run(['python3', str(root / 'tools/rpc.py'), 'arbitrum', method,
                        json.dumps(params)], check=True, text=True, capture_output=True)
    return json.loads(p.stdout)['result']


rows = []
for opportunity, send in zip(opps, sends):
    receipt = rpc('eth_getTransactionReceipt', [send['hash']])
    assert receipt and int(receipt['status'], 16) == 1
    block = rpc('eth_getBlockByNumber', [receipt['blockNumber'], False])
    used = int(receipt['gasUsed'], 16)
    effective = int(receipt['effectiveGasPrice'], 16)
    base = int(block['baseFeePerGas'], 16)
    priority = max(0, effective - base)
    gross = send['gain_wei']
    row = {'hash': send['hash'], 'block': int(receipt['blockNumber'], 16),
           'index': int(receipt['transactionIndex'], 16), 'gross_wei': gross,
           'gas_used': used, 'gas_cost_wei': used * effective,
           'actual_priority_wei': used * priority,
           'actual_priority_share': used * priority / gross,
           'bid_priority_share': opportunity['priority'] * used / gross,
           'effective_gas_price': effective, 'base_fee': base}
    rows.append(row)

out = root / 'scratch/grad-flatmoney-fees.json'
out.write_text(json.dumps(rows, indent=2))
for row in rows:
    print(row['hash'][:10], row['block'], row['index'],
          f"actual priority/gross {100*row['actual_priority_share']:.2f}%",
          f"bid/gross {100*row['bid_priority_share']:.2f}%")
