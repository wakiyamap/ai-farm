import json
from pathlib import Path

files = [Path('scratch/flux-usdt-receipt.json')] + [Path(f'scratch/flux-usdt-receipt-{i}.json') for i in range(7)]
for file in files:
    x = json.loads(file.read_text())['result']
    recipient = x['to'].lower()
    delta = {}
    for l in x['logs']:
        t = l['topics']
        if len(t) != 3 or t[0] != '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
            continue
        token = l['address'].lower()
        src = '0x'+t[1][-40:]
        dst = '0x'+t[2][-40:]
        n = int(l['data'], 16)
        if src == recipient:
            delta[token] = delta.get(token, 0)-n
        if dst == recipient:
            delta[token] = delta.get(token, 0)+n
    print(file.name, x['transactionHash'], 'block', int(x['blockNumber'],16), 'gas', int(x['gasUsed'],16), 'gwei', int(x.get('effectiveGasPrice',x.get('gasPrice')),16)/1e9, 'to',recipient)
    for token, n in delta.items():
        print(' ',token,n/1e18)
