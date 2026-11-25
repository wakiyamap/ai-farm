import json, subprocess

POOLS=['0x50bE5fE4de4efC3A0adAc6587254836972055423','0x7835d976516F82cA8a3Ed2942C4c6F9C4E44bb74','0x7ba283b1dDCdd0ABE9D0d3f36345645754315978','0xCDc3DD86C99b58749de0F697dfc1ABE4bE22216d','0xb7a5e68D89950a92F6C7dA33919D8415b1384A25','0xa8AFa64C91356FF2A3fAFd8324F0552EB8e76632','0x62F7790C49BA7F049DBb3EF2Cc1046A3103f025e']

def rpc(method,params):
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True)
    try: x=json.loads(p.stdout)
    except: return {'error':p.stderr.strip()[:200]}
    return x.get('result',x)

def call(addr,data,frm=None):
    tx={'to':addr,'data':data}
    if frm:tx['from']=frm
    return rpc('eth_call',[tx,'latest'])

def addr(x): return '0x'+x[-40:] if isinstance(x,str) and len(x)>=42 else x

for pool in POOLS:
    code=rpc('eth_getCode',[pool,'latest'])
    under=call(pool,'0x6f307dc3')
    loans=call(pool,'0x2d66da9f')
    try:
        n=int(loans[2+64:2+128],16)
        ls=['0x'+loans[2+128+64*i+24:2+128+64*(i+1)] for i in range(n)]
    except: n=-1;ls=[]
    print(json.dumps({'pool':pool,'code_bytes':(len(code)-2)//2 if isinstance(code,str) else code,'underlying':addr(under),'loan_count':n,'loans':ls[:20]}),flush=True)
