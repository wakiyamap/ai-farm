import json
import statistics
import subprocess

START = 1794276600  # 2026-11-10 02:10 UTC
QUERY = ("SELECT tx_hash, COUNT(*) n, MAX(block) blk, MAX(ts) ts, "
         "COUNT(DISTINCT json_extract(fields,'$.id')) markets "
         "FROM events WHERE source_id='morpho_blue.liquidate' AND chain='base' "
         "AND actor='0x5451c4b4ea335bfb71f75316594bb68d26d30917' "
         f"AND ts>={START} GROUP BY tx_hash")
raw = subprocess.check_output(['ledger', 'query', '--json', QUERY], text=True)
rows = [json.loads(x) for x in raw.splitlines() if x.strip()]
out = []
for row in rows:
    raw = subprocess.check_output(['python3', '/srv/farm/ws/tools/rpc.py',
                                   'base', 'eth_getTransactionReceipt',
                                   json.dumps([row['tx_hash']]), '--lane', 'research'],
                                  text=True)
    receipt = json.loads(raw)['result']
    item = dict(row)
    for key in ('gasUsed', 'effectiveGasPrice', 'l1Fee'):
        item[key] = int(receipt.get(key, '0x0'), 16)
    item['l2_eth'] = item['gasUsed'] * item['effectiveGasPrice'] / 1e18
    item['l1_eth'] = item['l1Fee'] / 1e18
    item['priority_gwei_upper'] = item['effectiveGasPrice'] / 1e9
    item['fee_usd_1800'] = (item['l2_eth'] + item['l1_eth']) * 1800
    out.append(item)
path = '/srv/farm/ws/scratch/morpho-batch-trial-cap.json'
with open(path, 'w') as f:
    json.dump(out, f, indent=2)
print('tx', len(out), 'liq', sum(x['n'] for x in out),
      'all_one_market', all(x['markets'] == 1 for x in out))
for key in ('n', 'gasUsed', 'effectiveGasPrice', 'l1Fee', 'fee_usd_1800'):
    vals = sorted(x[key] for x in out)
    print(key, 'min', vals[0], 'median', statistics.median(vals), 'max', vals[-1])
print('fee_gt_1_usd', sum(x['fee_usd_1800'] > 1 for x in out))
print('batch_gt_1_liq', sum(x['n'] > 1 for x in out))
