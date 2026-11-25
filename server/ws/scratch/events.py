import sys, json; sys.path.insert(0,'/srv/farm/ws/scratch')
from mc import rpc
top=json.load(open('/srv/farm/ws/scratch/uv2opt_top.json'))[:32]
addrs=[p['pair'] for p in top]
HEAD=159734889
R7={'fromBlock':hex(HEAD-302400),'toBlock':hex(HEAD)}
R30={'fromBlock':hex(HEAD-1296000),'toBlock':hex(HEAD)}
def T(sig):
    import subprocess
    return '0x'+subprocess.run(['cast','keccak',sig],capture_output=True,text=True).stdout.strip()[2:]
skim=T('Skim(address)'); swap=T('Swap(address,uint256,uint256,uint256,uint256,address)')
mint=T('Mint(address,uint256,uint256)'); burn=T('Burn(address,uint256,uint256,address)')
for name,tp,range_ in [('Skim 7d',skim,R7),('Swap 7d',swap,R7),('Mint 7d',mint,R7),('Burn 7d',burn,R7),
                       ('Skim 30d',skim,R30)]:
    r=rpc('eth_getLogs',[dict(range_, address=addrs, topics=[tp])])
    if isinstance(r,dict): print(name,'ERR',r); continue
    print(name, 'count', len(r), 'senders', sorted({('0x'+l['topics'][1][-40:]) for l in r})[:5])
