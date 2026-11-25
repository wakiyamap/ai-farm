import json, urllib.request, sys
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
for blk,tag in [('0x'+'191179d'.upper(),'26287069'),('latest','head')]:
    # recompute block hex properly
    if tag=='26287069': blk='0x'+hex(26287069)[2:]
    ret=rpc('ethereum','research','eth_call',[{"to":COMP,"data":enc_cm(0,100)},blk])
    b=ret[2:]
    w0=int(b[0:64],16); n=int(b[64:128],16)
    print(f"block {tag}: word0={hex(w0)} count={n}")
    # element offsets: n words starting at word 2
    offs=[int(b[128+i*64:192+i*64],16) for i in range(n)]
    print("first element offsets:", [hex(o) for o in offs[:5]], "last:", hex(offs[-1]))
    # each tuple data starts at byte 32+off; assume first field may be address: check
    for i,o in enumerate(offs):
        base=32+o  # bytes from end of header area? ABI: offsets are from start of the array's base type location = end of header (word1 area ends at 32+... ) 
        pass
    # ABI: dynamic array offsets measured from the end of its head area (after length word). The head area of the return: [offset, length]; then the dynamic array's own area starts at byte 32 (after length)? Offsets are relative to the start of the array's head-enclosed area. Let's locate TARGET in raw bytes empirically:
    pos=b.find(TARGET)
    print("target byte-position in return:", pos, " (multiple:", pos in (b.find(TARGET,pos+1),) ,")")
    # dump words around first element
    if n:
        e0=offs[0]
        # tuple 0 data at byte offset 32*? — empirical: find where TARGET sits relative to offsets
        pass
