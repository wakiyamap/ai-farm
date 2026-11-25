"""Run 8b0e: probe the trial's take at small sizes + cellar balances at given blocks (BLOCKS=latest,123,...)."""
import os, sys, importlib.util
from pathlib import Path
os.environ.setdefault('RPC_RELAY_URL', 'http://127.0.0.1:8545')
os.environ['RPC_LANE'] = 'research'
os.environ['BOT_MODE'] = 'paper'
spec = importlib.util.spec_from_file_location('bot', '/srv/farm/ws/bots/live/trial-ryeth-arb-arbitrum/bot.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
b.STATE = Path('/srv/farm/ws/scratch/r8b0e-cu.json')
b.CU_CAP = 10**9
sizes = [int(x) for x in os.environ.get('SIZES', '5,10,20,46,100,200,500,1000,2000').split(',')]
for blk in (sys.argv[1] if len(sys.argv) > 1 else 'latest').split(','):
    tag = blk if blk == 'latest' else hex(int(blk))
    cands = [(n, s * 10**15) for n in b.ROUTES for s in sizes]
    g = b.probe(cands, tag)
    print(blk, [(n, a / 1e18, x / 1e18) for (n, a), x in zip(cands, g) if x])

    def call(to, data):
        return b.rpc('eth_call', [{'to': to, 'data': data}, tag])
    bal = lambda t: int(call(t, '0x70a08231' + b.a(b.CELLAR)), 16) / 1e18
    print('  cellar WETH', bal(b.WETH), 'rETH', bal(b.RETH), 'wstETH', bal(b.WSTETH))
    for nm, sel in (('totalAssets', '0x01e1d114'), ('totalAssetsWithdrawable', '0xa8144e48'), ('totalSupply', '0x18160ddd')):
        try:
            print('  ', nm, int(call(b.CELLAR, sel), 16) / 1e18)
        except Exception as e:
            print('  ', nm, 'ERR', str(e)[:100])
