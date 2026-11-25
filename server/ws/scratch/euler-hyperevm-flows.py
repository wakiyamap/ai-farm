import json
from collections import defaultdict
from pathlib import Path

base = Path('/srv/farm/ws/scratch')
files = [base / f'euler-hyperevm-receipt-{i}.json' for i in range(4)]
files.insert(1, base / 'euler-hyperevm-receipt.json')
liq_topic = '0x8246cc71ab01533b5bebc672a636df812f10637ad720797319d5741d5ebb3962'
transfer_topic = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
for path in files:
    r = json.loads(path.read_text())['result']
    liqs = {l['topics'][1][-40:].lower() for l in r['logs'] if l['topics'][0] == liq_topic}
    flow = defaultdict(int)
    for l in r['logs']:
        if l['topics'][0] != transfer_topic or len(l['topics']) != 3:
            continue
        src, dst = (x[-40:].lower() for x in l['topics'][1:])
        for who in liqs:
            if src == who: flow[(who, l['address'].lower())] -= int(l['data'], 16)
            if dst == who: flow[(who, l['address'].lower())] += int(l['data'], 16)
    print(r['transactionHash'], 'block', int(r['blockNumber'], 16), 'gas', int(r['gasUsed'], 16),
          'price_gwei', round(int(r['effectiveGasPrice'], 16) / 1e9, 4), 'liquidators', liqs)
    print('net token deltas', dict(flow))
