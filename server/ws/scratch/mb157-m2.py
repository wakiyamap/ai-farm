import json, sys, subprocess
sys.path.insert(0,'scratch')
from importlib import import_module
m = import_module('mb157-measure')
rpc, call = m.rpc, m.call
M='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
ZEC='0xb2000000000000000000008501b13360000cb2ec'
XRP='0xcb585250f852c6c6bf90434ab21a00f02833a4af'
BTC='0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf'
ID_ZEC='0xe458a501c1103ca3b256f2bcb45d223263fb34b6349d82675494ce3a94ce1327'
O_ZEC='0xa3cb2d7204f47a468b82c6fab1ca9675e9f7a272'
seed=json.load(open('bots/paper/morpho-farmband-base/markets.json'))['markets']
def w(h,i): return int(h[2+i*64:2+i*64+64],16)
def keccak(h):
    return subprocess.run(['/opt/foundry/bin/cast','keccak',h if h.startswith('0x') else '0x'+h],capture_output=True,text=True).stdout.strip()
out={}
# 1) balanceOf for all seeded borrowers
for mid,mm in seed.items():
    coll=mm['coll']
    for b in mm['borrowers']:
        v=call(coll,'0x70a08231'+b[2:])
        bal=w(v,0)
        if bal>0: out.setdefault('nonzero',[]).append((mm['name'],b,bal))
print('nonzero balanceOf:', json.dumps(out.get('nonzero',[]),indent=0))
# 2) oracle aggregator getter candidates on ZEC oracle
for sel,name in [('0x245a7bfc','aggregator()'),('0x3ad59dbc','getAggregator()'),('0x0900f98f','getAggregator_v06()'),('0x385a8a39','latestRoundData()')]:
    try:
        v=call(O_ZEC,sel); out.setdefault('agg_probe',{})[name]= v if len(v)<200 else v[:80]+'...'
    except SystemExit as e: out.setdefault('agg_probe',{})[name]='revert'
print('oracle probes:', json.dumps(out.get('agg_probe'),indent=0))
# 3) accrueInterest variants on ZEC market params
p=call(M,'0x2c3c9157'+ID_ZEC[2:])
params=[ '0x'+p[2+i*64:2+i*64+40] for i in range(4)]+[p[2+256:2+320]]
cd='0x151c1ade'+''.join(x[2:] for x in params[:4])+params[4][2:]
try:
    r=call(M,cd); print('accrueInterest 0x151c1ade ->', r)
except SystemExit as e: print('accrueInterest 0x151c1ade ->',e)
cd2='0x0a2bdbd3'+ID_ZEC[2:]
try: print('accrueInterest(bytes32) ->', call(M,cd2))
except SystemExit as e: print('accrueInterest(bytes32) ->',e)
# price
try: print('price() ->', w(call(O_ZEC,'0xa035b1fe'),0))
except SystemExit as e: print('price() ->',e)
