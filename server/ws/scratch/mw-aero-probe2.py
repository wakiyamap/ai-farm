import json,urllib.request,os
URL=os.environ['RPC_RELAY_URL']+'/base?lane=research'
def call(to,data,blk):
    rq=urllib.request.Request(URL,data=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"%s"%blk]}).encode(),headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(rq,timeout=60).read())
    if 'error' in r: return ('ERR',r['error'])
    return r['result']
def h64(a): return a[2:].rjust(64,'0')
COMP='0xfbb21d0380bee3312b33c4353c8936a0f13ef26c'
LIQ='0x5ec88c79'
def liq(h,b):
    r=call(COMP,LIQ+h64(h[2:]),hex(b))
    if isinstance(r,str) and len(r)==2+192:
        w0=int(r[2:66],16)/1e18; w1=int(r[66:130],16)/1e18
        return w0,w1
    return ('ERR',r)
C='0xc8f8c2dde5dabaa585acdbc7fec3db639e97f3eb'
A='0x1a73d5b9fe5b1937db4ebd03ba3937211786fb57'
for h,b,tag in [(C,55224689,'C@burst-1'),(C,55150000,'C@pre-crash'),(C,54900000,'C@older'),
                (A,55297681,'A@burst'),(A,55224689,'A@burst-1')]:
    print(tag,b,liq(h,b))
