import json,subprocess
vaults=open('/srv/farm/ws/scratch/defrost_vaults.txt').read().split()
pools=['0xb61a0bd0952048b40091b950c247e109a2367f59','0x91264520f94c42680e5f41278d40842850ebe7d4','0x8e5e17c3ea63cd28afe78929f2645e45438d449a','0x921e28aa0fa99f4e6b41ceac91827e5ed5fe3d20','0x6cc4fbdec5a5c1c5030858fbb663fb82e63c5dce','0x80e23ba7fe91141b037cd81cf03a625886c41d9f']
g1,g2=vaults[:21],vaults[21:]+pools
t1='0xb2b14447b2fb5b250428a70cf03fd19f8ff7ee7e04a46ebe7824df2a0c91a9e3'
t2='0xc2575f648f3849a9f72cba2118e08fb31da7d8ead7dfc947dc59d00aadccfd9e'
wavax='0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'
transfer='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
HEAD=0x60799cb; START=0x5fd1a50
def getlogs(params):
    r=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','avalanche','eth_getLogs',json.dumps(params)],capture_output=True,text=True)
    if r.returncode!=0: return None
    return json.loads(r.stdout)['result']
# Control A: same chunked shape, no topics, all 42 addrs, last 3 chunks of 7d window
ctrl=[]
b=HEAD-3*9000
while b<HEAD:
    e=min(b+9000,HEAD)
    for g in (g1,g2):
        l=getlogs([{"fromBlock":hex(b),"toBlock":hex(e),"address":g}])
        ctrl+= (l or [])
        if len(ctrl)>100: break
    b=e+1
print("CONTROL notopic last-27k-blocks logs:",len(ctrl),flush=True)
# Control B: WAVAX Transfer 1 chunk positive control
l=getlogs([{"fromBlock":hex(HEAD-9000),"toBlock":hex(HEAD),"address":[wavax],"topics":[[transfer]]}])
print("CONTROL WAVAX Transfer logs:",len(l) if l is not None else "ERR",flush=True)
# Last-liquidate scan: backward 30 days (2.95M blocks) on both groups, stop at first hit
D30=HEAD-2_950_000
for name,g in (("v1(21 vaults)",g1),("v2(6 pools+15v1)",g2)):
    found=None; b=HEAD
    scanned=0
    while b>D30:
        e=min(b,HEAD)
        if e-b>9999: e=b+9999
        l=getlogs([{"fromBlock":hex(e-9999),"toBlock":hex(e),"address":g,"topics":[[t1,t2]]}])
        scanned+=1
        if l is None: print("ERR chunk",hex(e-9999),flush=True)
        elif l: found=l[-1]; break
        b=e-10000
    print(f"LAST LIQ {name}: found={found is not None} at_block={int(found['blockNumber'],16) if found else None} chunks_scanned={scanned}",flush=True)
    if found: print(json.dumps(found)[:400],flush=True)
