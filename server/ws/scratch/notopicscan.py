import json,subprocess
vaults=open('/srv/farm/ws/scratch/defrost_vaults.txt').read().split()
pools=['0xb61a0bd0952048b40091b950c247e109a2367f59','0x91264520f94c42680e5f41278d40842850ebe7d4','0x8e5e17c3ea63cd28afe78929f2645e45438d449a','0x921e28aa0fa99f4e6b41ceac91827e5ed5fe3d20','0x6cc4fbdec5a5c1c5030858fbb663fb82e63c5dce','0x80e23ba7fe91141b037cd81cf03a625886c41d9f']
g1,g2=vaults[:21],vaults[21:]+pools
HEAD=0x60799cb; START=0x5fd1a50
logs=[]; errs=0
b=START
while b<HEAD:
    e=min(b+9000,HEAD)
    for g in (g1,g2):
        r=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','avalanche','eth_getLogs',json.dumps([{"fromBlock":hex(b),"toBlock":hex(e),"address":g}])],capture_output=True,text=True)
        if r.returncode!=0: errs+=1
        else: logs+=json.loads(r.stdout)['result']
    b=e+1
print("7d no-topic logs on 42 contracts:",len(logs),"errs:",errs)
import collections
c=collections.Counter((l['address'].lower(),l['topics'][0][:10]) for l in logs)
for k,v in c.most_common(10): print(k,v)
