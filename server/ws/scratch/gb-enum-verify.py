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
TARGET='0x56631dcb1ea548d2629e82e01375090ed1f81b7e'
def enc_cm(sel,offset,size):
    return '0x'+sel+CM[2:].lower().rjust(64,'0')+hex(offset)[2:].rjust(64,'0')+hex(size)[2:].rjust(64,'0')
def decode_accounts(ret):
    b=ret[2:]; W=[b[i:i+64] for i in range(0,len(b),64)]
    n=int(W[1],16)
    out=[]
    for k in range(n):
        ptr=int(W[2+k],16)          # bytes, measured from the first position after the array length word (word index 2)
        base=2+ptr//32              # tuple head start word
        out.append('0x'+W[base][-40:])   # field 0 = account address
    return out
BLK='0x'+hex(26287069)[2:]
accts=decode_accounts(rpc('ethereum','research','eth_call',[{"to":COMP,"data":enc_cm('3b007fb9',0,100)},BLK]))
print("block 26287069 accounts:", len(accts), "TARGET enumerated:", TARGET in accts)
print("accounts:", accts[:6], "...")
# positive control: isLiquidatable(TARGET, 10000) == 1 at 26287069
d='0x8340e24d'+TARGET[2:].lower().rjust(64,'0')+'2710'.rjust(64,'0')
r=rpc('ethereum','research','eth_call',[{"to":CM,"data":d},BLK])
print("isLiquidatable(TARGET) at 26287069:", int(r[2:],16))
# a healthy account control at the same block: first account not TARGET
h=accts[0] if accts[0]!=TARGET else accts[1]
d2='0x8340e24d'+h[2:].lower().rjust(64,'0')+'2710'.rjust(64,'0')
r2=rpc('ethereum','research','eth_call',[{"to":CM,"data":d2},BLK])
print("isLiquidatable(control", h,") at 26287069:", int(r2[2:],16))
