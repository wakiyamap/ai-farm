import subprocess, json

TXS = ["0xc1ed8f1b8c1f3c54121246d74eefb8f44a6cd2b41b9f32d292a6317ae5fa9ac4",
       "0x880672c1c047cc1736d786e9acf9a60f42b7d29b87b66661eb758a263f853330",
       "0x150ed8be741e67b002541e77169a8e350c5ee9777ec223b1ad11f8023121e365",
       "0xe38549aca70bcfbc65d3d178db6c7fe677d1bdaed8f08449bf403c428b7f8c8d"]
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def rpc(method, params):
    r = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum', method, json.dumps(params)],
                       capture_output=True, text=True)
    j = json.loads(r.stdout)
    return j.get('result')


def sel(sig):
    return subprocess.run(['cast', 'sig', sig], capture_output=True, text=True).stdout.strip()


DEC = {}


def decimals(tok):
    if tok not in DEC:
        res = rpc('eth_call', [{"to": tok, "data": sel('decimals()')}, "latest"])
        DEC[tok] = int(res, 16) if res else None
    return DEC[tok]


for tx in TXS:
    rec = rpc('eth_getTransactionReceipt', [tx])
    if rec is None:
        print(tx, 'no receipt')
        continue
    txobj = rpc('eth_getTransactionByHash', [tx])
    frm = txobj['from']
    print('tx', tx[:22], 'from', frm, 'gasUsed', int(rec['gasUsed'], 16),
          'status', rec['status'], 'gasPriceGwei', int(rec.get('effectiveGasPrice', '0x0'), 16) / 1e9)
    for l in rec['logs']:
        if l['topics'][0] != TRANSFER or len(l['topics']) != 3:
            continue
        to = '0x' + l['topics'][2][-40:]
        fr = '0x' + l['topics'][1][-40:]
        tok = l['address']
        amount = int(l['data'], 16)
        d = decimals(tok)
        hum = amount / 10 ** d if d else amount
        if to.lower() == frm.lower():
            print('   IN  %s %s' % (tok, hum))
        if fr.lower() == frm.lower():
            print('   OUT %s %s' % (tok, hum))
