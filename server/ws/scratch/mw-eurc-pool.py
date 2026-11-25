import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']
def call(to,data,label):
    p={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"latest"]}
    rq=urllib.request.Request(f"{URL}/base?lane=research",data=json.dumps(p).encode(),headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(rq,timeout=90).read())
    if 'error' in r: print("ERR",label,r['error']); return None
    return r['result']
def h(x): return int(x,16)
P3="0x4dbdcb087992404ea9b14fa83cc695b02797f39a"   # EURC/WETH fee100 pool (constructor P3, attempt 634)
P1="0x0d6116854f9c17b6617ebf24ffe6806534d3c106"   # bot P1 USDC/WETH? verify from bot.js below
M_EURC="0xb682c840b5f4fc58b20769e691a6fa1305a501a2"  # mEURC borrow market
MORPHO="0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb"
bal=lambda tok,who: call(tok,"0x70a08231"+who[2:].rjust(64,'0'),"bal")
t0=call(P3,"0x0dfe1681","token0"); t1=call(P3,"0xd07ca607","token1")
fee=call(P3,"0xdd59e9f2","fee")
s0=call(P3,"0x3850c7bd","slot0")
und=call(M_EURC,"0x6f3ffca6","underlying")
EURC=und if und else None
words=[] if not s0 else [int(s0[2+i:i+66],16) for i in range(0,len(s0)-2,64)]
sqrt=words[0] if words else 0
print("P3 token0",t0,"token1",t1,"fee",h(fee) if fee else None)
print("slot0 sqrtPriceX96",sqrt,"tick",hex(words[1]) if words else None)
if EURC:
    print("EURC underlying",EURC)
    pb=h(bal(EURC,P3)); print("pool EURC balance %.2f"%(pb/1e6))
    mb=h(bal(EURC,MORPHO)); print("morpho EURC balance %.4f"%(mb/1e6))
    WETH=t0 if (t0 and h(t0)!=h(EURC)) else t1
    wb=h(bal(WETH,P3)); print("pool WETH(%.14s) balance %.5f"%(WETH,wb/1e18))
    price=(sqrt/2**96)**2
    print("EURC per WETH (spot) %.2f ; EURC out for 0.034 WETH after fee: %.2f"%(price,price*0.034*(1-h(fee)/1e6)))
