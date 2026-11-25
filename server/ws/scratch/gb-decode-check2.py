import json, urllib.request
RELAY="http://127.0.0.1:8545"
def rpc(chain, lane, method, params, timeout=40):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{RELAY}/{chain}?lane={lane}",data=body,headers={"content-type":"application/json"})
    j=json.loads(urllib.request.urlopen(req,timeout=timeout).read())
    if "error" in j: raise SystemExit(f"error: {j['error']}")
    return j["result"]
CM='0x1293a69e4ad4a93293a06b6303104be35bdd83af'
COMP='0x81cb9ea2d59414ab13ec0567efb09767ddbe897a'
TARGET='56631dcb1ea548d2629e82e01375090ed1f81b7e'
SEL='3b007fb9'
def enc_cm(offset,size):
    return '0x'+SEL+CM[2:].lower().rjust(64,'0')+hex(offset)[2:].rjust(64,'0')+hex(size)[2:].rjust(64,'0')
for blk,tag in [('0x'+hex(26287069)[2:],'26287069'),('latest','head')]:
    ret=rpc('ethereum','research','eth_call',[{"to":COMP,"data":enc_cm(0,100)},blk])
    b=ret[2:]
    n=int(b[64:128],16)
    offs=[int(b[128+i*64:192+i*64],16) for i in range(n)]
    L=len(b)//2
    pos=b.find(TARGET)
    # solve tuple data area start s: last tuple must end exactly at end of return
    s = L - offs[n-1] - 256
    print(f"block {tag}: n={n} bytes={L//2} s(solve)={s} offs0={offs[0]}")
    # which tuple holds TARGET, at which word
    for k in range(n):
        base=s+offs[k]
        if base <= pos < base+256:
            w=(pos-base)//32
            print(f"  TARGET in tuple {k} (address field word {w}); tuple0 first words:")
            for ww in range(8):
                print("   ", b[base+ww*32:base+ww*32+64])
            break
