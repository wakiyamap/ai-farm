import sys; sys.path.insert(0,'/srv/farm/ws/scratch')
exec(open('/srv/farm/ws/scratch/uv2opt.py').read())
WETH='0x4200000000000000000000000000000000000006'
USDC='0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'
DAI='0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'
OP='0x4200000000000000000000000000000000000042'
def addr(w): return '0x'+w[-40:]
def enc_addr(a): return '00'*12+a[2:]
def gp(a,b):
    r=call(F, sel('getPair(address,address)')+enc_addr(a)+enc_addr(b))
    return None if isinstance(r,dict) else addr(r)
pairs={}
for name,(a,b) in {'WETH-USDC':(WETH,USDC),'WETH-DAI':(WETH,DAI),'WETH-OP':(WETH,OP),'USDC-DAI':(USDC,DAI)}.items():
    p=gp(a,b); pairs[name]=p; print(name,p)
import json; open('/srv/farm/ws/scratch/uv2opt_pairs.json','w').write(json.dumps(pairs))
