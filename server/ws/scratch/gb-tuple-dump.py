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
def enc_cm(offset,size):
    return '0x3b007fb9'+CM[2:].lower().rjust(64,'0')+hex(offset)[2:].rjust(64,'0')+hex(size)[2:].rjust(64,'0')
ret=rpc('ethereum','research','eth_call',[{"to":COMP,"data":enc_cm(0,100)},'latest'])
b=ret[2:]; W=[b[i:i+64] for i in range(0,len(b),64)]
n=int(W[1],16); print("N =", n)
# dump all tuple heads (4 words each) per pointer
for k in range(min(n,6)):
    ptr=int(W[2+k],16); base=2+ptr//32
    print("tuple",k,":", [W[base+i][:64] for i in range(4)])

# tail words beyond tuples
last_tuple_words = 2 + int(W[2+n-1],16)//32 + 4
print("total words:", len(W), "after tuples:", len(W)-last_tuple_words)
for i in range(last_tuple_words, len(W)):
    print("tail word", i-last_tuple_words, W[i])
