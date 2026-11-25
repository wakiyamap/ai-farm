import json, sys
sys.path.insert(0,'/srv/farm/ws/scratch')
from rpcu import rpc
FACTORY='0x78Df1CF5bf06a7f27f2ACc580B934238C1b80D50'
N=193; SEL='378cdb62'
offsets=b''; structs=b''
for i in range(N):
    d=SEL+format(i,'064x')
    offsets+=bytes.fromhex(format(0x20*N+160*i,'064x'))
    structs+=bytes.fromhex(FACTORY[2:].lower().rjust(64,'0'))
    structs+=bytes.fromhex(format(1,'064x'))
    structs+=bytes.fromhex(format(0x60,'064x'))
    structs+=bytes.fromhex(format(len(d)//2,'064x')+d.ljust(64,'0'))
calldata='0x82ad56cb'+format(0x20,'064x')+format(N,'064x')+(offsets+structs).hex()
res=rpc('eth_call',[{'to':'0xcA11bde05977b3631167028862bE2a173976CA11','data':calldata},'latest'])[2:]
off2=int(res[64:128],16)
ba=int(res[off2*2:off2*2+64],16)
base=off2*2+64
vaults=[]
for i in range(ba):
    o=int(res[base+i*64:base+i*64+64],16)
    L=int(res[base+o*2:base+o*2+64],16)
    v=res[base+o*2+64:base+o*2+64+L*2]
    vaults.append('0x'+v[-40:] if L>=40 else None)
ok=[v for v in vaults if v]
print('decoded',len(vaults),'nonempty',len(ok))
json.dump(ok,open('/srv/farm/ws/scratch/euler_arb_vaults.json','w'))
print(ok[:3])
