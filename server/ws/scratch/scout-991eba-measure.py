import json, subprocess, statistics, datetime, pathlib

ROOT = '/srv/farm/ws'
OUT = pathlib.Path(ROOT) / 'scratch/scout-991eba-measure.json'
START = 1794881495
HAI_USD = 1.2329471955023232  # coins.llama.fi 1795478887
ETH_USD = 1701.3850219        # coins.llama.fi 1795486280
ORACLE = '0x519011d32806f324364201c5c98579aec55d9011'  # OP, official relayer getter in lead 213
CTYPES = {x.encode().hex().ljust(64, '0') for x in ('OP','RETH','TBTC','VELO','WETH')}

def run(args):
    p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if p.returncode: raise RuntimeError(f'{args}: {p.stderr[:400]} {p.stdout[:400]}')
    return p.stdout

def rpc(method, params):
    out = json.loads(run(['python3','tools/rpc.py','optimism',method,json.dumps(params)]))
    if 'error' in out: raise RuntimeError(f'{method}: {out["error"]}')
    return out['result']

sql = """WITH batch AS (SELECT tx_hash,MIN(block) AS block,MIN(ts) AS ts,MIN(actor) AS actor,COUNT(*) AS rewards FROM events WHERE chain='optimism' AND source_id='hai.oracle_job_reward' AND ts>=1794881495 GROUP BY tx_hash HAVING COUNT(*)>=4), ranked AS (SELECT *,ROW_NUMBER() OVER (ORDER BY rewards DESC,block DESC) AS rn FROM batch) SELECT tx_hash,block,ts,actor,rewards,rn FROM ranked WHERE rn<=5 OR (rn>5 AND (rn-6)%11=0) ORDER BY rn LIMIT 20"""
rows = [json.loads(x) for x in run(['ledger','query','--json',sql]).splitlines()]
assert len(rows) == 20

# Find the block at the timestamp boundary, based on actual OP block timestamps.
lo, hi = 159600000, int(rpc('eth_blockNumber', []), 16)
while lo < hi:
    mid = (lo + hi) // 2
    b = rpc('eth_getBlockByNumber', [hex(mid),False])
    if int(b['timestamp'],16) < START: lo = mid+1
    else: hi = mid
start_block = rpc('eth_getBlockByNumber',[hex(lo),False])
head = rpc('eth_getBlockByNumber',['latest',False])

for row in rows:
    receipt = rpc('eth_getTransactionReceipt',[row['tx_hash']])
    tx = rpc('eth_getTransactionByHash',[row['tx_hash']])
    bnum = row['block']
    last = int(rpc('eth_call',[{'to':ORACLE,'data':'0xc8f33c91'},hex(bnum-1)]),16)
    due = last + 3600
    # OP 2-second blocks. If take is later, find the earliest eligible block exactly.
    if row['ts'] >= due:
        due_block = bnum
        while due_block > bnum-30:
            prev = rpc('eth_getBlockByNumber',[hex(due_block-1),False])
            if int(prev['timestamp'],16) < due: break
            due_block -= 1
        delay_blocks = bnum - due_block
    else:
        delay_blocks = None
    relayer_items = [l['topics'][1][2:].lower().rstrip('0') for l in receipt['logs'] if l['address'].lower() == '0x6270403b908505f02da05be5c1956abb59fdb3a6' and len(l['topics']) > 1]
    item_names = []
    for l in receipt['logs']:
        if l['address'].lower() == '0x6270403b908505f02da05be5c1956abb59fdb3a6' and len(l['topics']) > 1:
            try: item_names.append(bytes.fromhex(l['topics'][1][2:]).rstrip(b'\x00').decode())
            except: pass
    gas_used = int(receipt['gasUsed'],16)
    effective = int(receipt['effectiveGasPrice'],16)
    l1_fee = int(receipt.get('l1Fee','0x0'),16)
    row.update(taker=row['actor'], tx_from=tx['from'], tx_index=int(receipt['transactionIndex'],16),
               due=due, blocks_from_takeable=delay_blocks,
               priority_gwei=int(tx.get('maxPriorityFeePerGas','0x0'),16)/1e9,
               gas_used=gas_used, gas_usd=(gas_used*effective+l1_fee)/1e18*ETH_USD,
               gross_usd=row['rewards']*0.05*HAI_USD, items=item_names,
               l1_fee_wei=l1_fee, effective_gwei=effective/1e9)
    OUT.write_text(json.dumps({'start_block':lo,'start_ts':int(start_block['timestamp'],16),
        'head_block':int(head['number'],16),'head_ts':int(head['timestamp'],16),
        'rows':rows},indent=2))

print(json.dumps({'start_block':lo,'start_ts':int(start_block['timestamp'],16),
    'head_block':int(head['number'],16),'head_ts':int(head['timestamp'],16),
    'sample':len(rows), 'median_blocks':statistics.median(x['blocks_from_takeable'] for x in rows if x['blocks_from_takeable'] is not None),
    'median_priority_gwei':statistics.median(x['priority_gwei'] for x in rows),
    'median_gross_usd':statistics.median(x['gross_usd'] for x in rows),
    'median_gas_usd':statistics.median(x['gas_usd'] for x in rows),
    'unique_item_sets':sorted({tuple(x['items']) for x in rows}),
    'row_summaries':[{k:x[k] for k in ('tx_hash','taker','rewards','blocks_from_takeable','priority_gwei','gross_usd','gas_usd','tx_index','items')} for x in rows]},indent=2))
