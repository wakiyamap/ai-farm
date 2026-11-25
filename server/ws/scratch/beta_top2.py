import subprocess, json

# (tx, caller from Liquidate event)
SAMPLES = [("0xe0575b2b9b06edd51ad76359644f721c2e40a1d0e292e5c09932b22193df4977", "0x4659362bb53d0d7c97c136753ba512dadfe2467b"),
           ("0x68bafd25382d39a66ca815a8fc5e765ab05ca83da43150cc0a0aee7b91537db4", "0xde7431be8ff63fe061dd0c51aa8b5ac7093c6f19")]
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def rpc(method, params):
    r = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum', method, json.dumps(params)],
                       capture_output=True, text=True)
    return json.loads(r.stdout).get('result')


def sel(sig):
    return subprocess.run(['cast', 'sig', sig], capture_output=True, text=True).stdout.strip()


DEC = {}


def decimals(tok):
    if tok not in DEC:
        res = rpc('eth_call', [{"to": tok, "data": sel('decimals()')}, "latest"])
        DEC[tok] = int(res, 16) if res else 18
    return DEC[tok]


for tx, caller in SAMPLES:
    rec = rpc('eth_getTransactionReceipt', [tx])
    print('=== tx', tx[:20], 'caller', caller, 'gasUsed', int(rec['gasUsed'], 16),
          'gasPriceGwei', round(int(rec.get('effectiveGasPrice', '0'), 16) / 1e9, 4))
    for l in rec['logs']:
        if l['topics'][0] != TRANSFER or len(l['topics']) != 3:
            continue
        fr = '0x' + l['topics'][1][-40:]
        to = '0x' + l['topics'][2][-40:]
        tok = l['address']
        amt = int(l['data'], 16) / 10 ** decimals(tok)
        tag = []
        if to.lower() == caller:
            tag.append('->CALLER')
        if fr.lower() == caller:
            tag.append('CALLER->')
        print('  %s %14.8f %s %s->%s' % (tok, amt, ' '.join(tag), fr[:10], to[:10]))
