import json, subprocess, sys

def rpc(method, params):
    import tempfile, os
    f=tempfile.NamedTemporaryFile("w",suffix=".json",delete=False)
    json.dump(params,f); f.close()
    r = subprocess.run(["python3","tools/rpc.py","polygon",method,"--params-file",f.name],
                       capture_output=True, text=True)
    os.unlink(f.name)
    try:
        d = json.loads(r.stdout)
    except Exception:
        print("RPC FAIL:", r.stdout[:300], r.stderr[:300]); sys.exit(1)
    if "error" in d:
        print("RPC ERR:", json.dumps(d["error"])[:300]); sys.exit(1)
    return d["result"]

def castcalldata(sig, *args):
    r = subprocess.run(["cast","calldata",sig,*[str(a) for a in args]],
                       capture_output=True, text=True)
    if r.returncode: print("CAST FAIL:", r.stderr[:300]); sys.exit(1)
    return r.stdout.strip()

def decode_addrs(hexres):
    # aggregate3 returns (Result[])(bool,bytes)[] -> each returnData is 32-byte address word
    h = hexres[2:]
    # skip selector-free result: offset(1) len(1) then per item: success(32) roffset(32) then dyn bytes...
    # easier: find all 20-hex tail patterns where preceding success=1 and bytes length=32
    words = [h[i:i+64] for i in range(0,len(h),64)]
    addrs=[]
    i=0
    # layout: [0]=off [1]=arrlen [2..]=heads(success word? no: tuple (bool,bytes) dynamic -> head offsets only)
    # Result[] dynamic array: arrlen then per item a head offset to tuple data; tuple data: bool word, bytes offset word(=0x20), len word, data word
    n=int(words[1],16)
    base=2
    for k in range(n):
        off=int(words[base+k],16)//32
        p=base+off
        succ=int(words[p],16); boff=int(words[p+1],16)//32
        q=p+boff
        blen=int(words[q],16)
        if blen>=32:
            addrs.append("0x"+words[q+1][-40:])
        else:
            addrs.append(None)
    return addrs

REGS = [
 ("uniswap","0x0Ac4C7b794f3D7e7bF1093A4f179bA792CF15055",61),
 ("sushi","0x97686103B3E7238Ca6c2C439146B30adBd84a593",17),
 ("quick","0xAeC731F69Fa39aD84c7749E913e3bC227427Adfd",143),
 ("retro","0xcAC19d43C9558753d7535978A370055614Ce832E",81),
 ("ascent","0x7b9c2f68f16c3618bb45616fb98d83f94fd7062e",1),
]
MC="0xcA11bde05977b3631167028862bE2a173976CA11"
calls=[]; labels=[]
for name,reg,n in REGS:
    for i in range(n):
        idx=f"{i:#066x}"
        calls.append(f"({reg},true,0x5893253c{idx[2:]})")
        labels.append((name,i))
cd = castcalldata("aggregate3((address,bool,bytes)[])", "["+",".join(calls)+"]")
res = rpc("eth_call",[{"to":MC,"data":cd},"latest"])
addrs = decode_addrs(res)
vaults=[]
for (name,i),a in zip(labels,addrs):
    if a: vaults.append((name,a))
print("vaults:",len(vaults))
json.dump(vaults,open("scratch/gamma-vaults.json","w"))
