import json, urllib.request, sys
RELAY="http://127.0.0.1:8545"
CETH="0xe65cdb6479bac1e22340e4e755fae7e509ecd06c"
RECIPIENT="0x8f10b468b06c6fd214b65f87778827f7d113f996"
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(RELAY+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", method, json.dumps(r["error"])); sys.exit(1)
    return r["result"]
def call(sig, extra="", tag="latest"):
    return rpc("eth_call",[{"to":CETH,"data":sig+extra}, tag])
def h(x): return int(x,16) if x not in (None,"0x","") else None
supply=h(call("0x18160ddd"))/1e8
rate=h(call("0xbd6d894d"))/1e18
abn=h(call("0x6c540baf"))
srb=h(call("0xae9d70b0"))
print(f"totalSupply={supply:.2f} units, exchangeRateCurrent={rate:.10f} ETH/unit, accrualBlock={abn}, supplyRatePerBlock={srb}")
blk=rpc("eth_getBlockByNumber",[rpc("eth_blockNumber",[]),False])
basefee=int(blk["baseFeePerGas"],16)/1e9
print(f"head={int(blk['number'],16)} baseFeePerGas={basefee:.3f} gwei")
for tag in [26365189,26365190,26365191,26366000,26369000]:
    b=h(call("0x70a08231",RECIPIENT[2:],hex(tag)))
    print(f"balanceOf recipient @{tag}:", b/1e8 if b is not None else b)
