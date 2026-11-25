import subprocess, json
REG="0xfb4de84c4375d7c8577327153de88f58f69eec81"
sel="a7666d4b"
for i in range(33):
    data="0x"+sel+("%064x"%i)
    out=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_call",'[{"to":"%s","data":"%s"},"latest"]'%(REG,data)],capture_output=True,text=True).stdout
    res=json.loads(out)["result"][2:]
    w=[res[j*64:(j+1)*64] for j in range(14)]
    pool="0x"+w[1][-40:]
    name=bytes.fromhex(w[4]).rstrip(b"\0").decode(errors="replace")
    rm=int(w[11],16); ap=int(w[10],16)
    print(i,repr(name),pool,"approved" if ap else "notapproved","REMOVED" if rm else "")
