#!/usr/bin/env python3
"""Sample 5 polygon cv3 buys: spot value vs paid (gross), gas USD, caller EOA check."""
import json, subprocess, urllib.request

def rpc(chain, method, params):
    out = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', chain, method, json.dumps(params)],
                         capture_output=True, text=True)
    j = json.loads(out.stdout)
    return j.get('result', j)

sc = json.load(open('/srv/farm/ws/scratch/cv3-poly-v3-scan.json'))
buys = [l for l in sc['logs'] if l['kind'] == 'BUY']
# pick: incumbent WBTC 23k, incumbent WETH 4930, incumbent WETH 2930, new-window WBTC 0x5ac9bc14, residue 0xc37184b6 1899.69
picks = []
for l in buys:
    key = (l['idx_addrs'][0], l['data'][0])
    picks.append((l['block'], l['tx'], l['idx'], l['idx_addrs'][0], l['idx_addrs'][1], l['data']))
want = [(97334219,'0x10e3c6c054e709c4878acc831048a470ce97951a'), (97334220,'0x10e3c6c054e709c4878acc831048a470ce97951a'),
        (97332764,'0x10e3c6c054e709c4878acc831048a470ce97951a'), (97557840,'0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd'),
        (97334218,'0x30a9f049060c761d3e3b1e487450e8cdc409c693')]
sel = []
for blk, who in want:
    for p in picks:
        if p[0]==blk and p[3]==who: sel.append(p); break

WETH='0x7ceb23fd6bc0add59e62ac25578270cff1b9f619'
WBTC='0x1bfd67037b42cf73acf2047067bd4f2c47d9bfd6'
DEC={WETH:18, WBTC:8}
def hist(coins, ts):
    url = f"https://coins.llama.fi/prices/historical/{ts}/{coins}?searchWidth=6h"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)['coins']

# EOA check
for a in sorted(set(l['idx_addrs'][0] for l in buys)):
    c = rpc('polygon','eth_getCode',[a,'latest'])
    print('code', a[:10], 'len', len(c)//2-1 if isinstance(c,str) else c)

pol = rpc('polygon','eth_getBlockByNumber',['latest',False])
ts_head = int(pol['timestamp'],16)
pp = hist('coingecko:polygon-ecosystem-token', ts_head)
pol_px = list(pp.values())[0]['price']
print('POL price USD', pol_px, 'source coins.llama.fi @head')

for blk, tx, txi, buyer, col, (paid, amt) in sel:
    b = rpc('polygon','eth_getBlockByNumber',[hex(blk),False])
    tsb = int(b['timestamp'],16)
    rc = rpc('polygon','eth_getTransactionReceipt',[tx])
    gas = int(rc['gasUsed'],16)*int(rc['effectiveGasPrice'],16)
    px = hist(f"polygon:{col}", tsb)
    spot = list(px.values())[0]['price']
    collateral = amt/10**DEC[col]
    val = collateral*spot
    gross = val - paid/1e6
    print(f"blk {blk} txidx {txi} buyer {buyer[:10]} col {col[:8]} paid {paid/1e6:.2f} USDC.e got {collateral:.6f} @ ${spot:,.0f} -> gross ${gross:.2f} | gasUsed {int(rc['gasUsed'],16)} gasUSD ${gas/1e18*pol_px:.4f} tx {tx[:18]}")
