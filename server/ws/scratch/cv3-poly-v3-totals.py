#!/usr/bin/env python3
import json, subprocess, urllib.request
def rpc(chain, method, params):
    out = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', chain, method, json.dumps(params)], capture_output=True, text=True)
    return json.loads(out.stdout).get('result')
def hist(coins, ts):
    url = f"https://coins.llama.fi/prices/historical/{ts}/{coins}?searchWidth=6h"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)['coins']
sc = json.load(open('/srv/farm/ws/scratch/cv3-poly-v3-scan.json'))
buys = [l for l in sc['logs'] if l['kind']=='BUY']
WETH='0x7ceb23fd6bc0add59e62ac25578270cff1b9f619'; WBTC='0x1bfd67037b42cf73acf2047067bd4f2c47d9bfd6'
DEC={WETH:18, WBTC:8}
blkts, spots = {}, {}
tot_paid = tot_gross = 0
bybuyer = {}
for l in buys:
    b = l['block']
    if b not in blkts:
        blkts[b] = int(rpc('polygon','eth_getBlockByNumber',[hex(b),False])['timestamp'],16)
    tsb = blkts[b]
    key = tsb
    if key not in spots:
        spots[key] = hist(f"polygon:{WETH},polygon:{WBTC}", tsb)
    paid, amt = l['data']
    col = l['idx_addrs'][1]
    spot = spots[key][f"polygon:{col}"]['price']
    gross = amt/10**DEC[col]*spot - paid/1e6
    tot_paid += paid/1e6; tot_gross += gross
    bb = bybuyer.setdefault(l['idx_addrs'][0], [0,0.0,0.0])
    bb[0]+=1; bb[1]+=paid/1e6; bb[2]+=gross
    print(l['block'], l['idx'], l['idx_addrs'][0][:10], col[:8], f"paid {paid/1e6:.2f} gross {gross:+.2f}")
print(f"TOTAL buys {len(buys)} paid ${tot_paid:,.0f} gross ${tot_gross:,.0f} (spot-vs-paid, coins.llama.fi hist)")
for k,v in sorted(bybuyer.items(), key=lambda x:-x[1][2]): print(k[:12], 'buys',v[0], f"paid ${v[1]:,.0f} gross ${v[2]:,.2f}")
# fresh-address eth_call buyCollateral(WETH, 0, 100000) on cUSDCv3
s = subprocess.run(['/opt/foundry/bin/cast','sig','buyCollateral(address,uint256,uint256)'],capture_output=True,text=True).stdout.strip()
data = s + WETH[2:].rjust(64,'0') + format(0,'064x') + format(100000,'064x')
r = rpc('polygon','eth_call',[{'from':'0xFeDA7E24a0E7F0b01F1B6a0af00dd0B1B1fe5eB0','to':'0xF25212E676D1F7F89Cd72fFEe66158f541246445','data':data},'latest'])
print('eth_call buyCollateral from fresh addr ->', str(r)[:200])
