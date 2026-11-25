import json,subprocess,os
vaults=open('/srv/farm/ws/scratch/defrost_vaults.txt').read().split()
pools=['0xb61a0bd0952048b40091b950c247e109a2367f59','0x91264520f94c42680e5f41278d40842850ebe7d4','0x8e5e17c3ea63cd28afe78929f2645e45438d449a','0x921e28aa0fa99f4e6b41ceac91827e5ed5fe3d20','0x6cc4fbdec5a5c1c5030858fbb663fb82e63c5dce','0x80e23ba7fe91141b037cd81cf03a625886c41d9f']
addrs=vaults+pools
g1,g2=addrs[:21],addrs[21:]
t1='0xb2b14447b2fb5b250428a70cf03fd19f8ff7ee7e04a46ebe7824df2a0c91a9e3'
t2='0xc2575f648f3849a9f72cba2118e08fb31da7d8ead7dfc947dc59d00aadccfd9e'
HEAD=0x60799cb; START=0x5fd1a50; STEP=9000
logs=[]; errs=0
b=START
while b<HEAD:
    e=min(b+STEP,HEAD)
    for gi,g in enumerate((g1,g2)):
        p=json.dumps([{"fromBlock":hex(b),"toBlock":hex(e),"address":g,"topics":[[t1,t2]]}])
        r=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','avalanche','eth_getLogs',p],capture_output=True,text=True)
        if r.returncode!=0: errs+=1; print("ERR",hex(b),gi,r.stderr[:120],flush=True)
        else:
            try: logs+=json.loads(r.stdout)['result']
            except Exception as ex: errs+=1; print("PARSE",hex(b),gi,r.stdout[:120],flush=True)
    b=e+1
json.dump({'logs':logs,'chunks_with_errors':errs,'range':[START,HEAD]},open('/srv/farm/ws/scratch/liq_scan_result.json','w'))
print("DONE logs:",len(logs),"errs:",errs,flush=True)
