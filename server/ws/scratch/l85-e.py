import json, urllib.request, sys
RELAY="http://127.0.0.1:8545"
CETH="0xe65cdb6479bac1e22340e4e755fae7e509ecd06c"
RECIPIENT="0x8f10b468b06c6fd214b65f87778827f7d113f996"
SEL={"totalSupply":"0x18160ddd","balanceOf":"0x70a08231","exchangeRateCurrent":"0xbd6d894d","accrualBlockNumber":"0x6c540baf","supplyRatePerBlock":"0xae9d70b0","borrowRatePerBlock":"0xc39f0594"}
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(RELAY+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", method, json.dumps(r["error"])); sys.exit(1)
    return r["result"]
def ceth_call(sig, extra="", tag="latest"):
    return rpc("eth_call",[{"to":CETH,"data":sig+extra}, tag])
ts=ceth_call(SEL["totalSupply"]); supply=int(ts,16); print("totalSupply:", supply/1e8, "cETH units")
er=ceth_call(SEL["exchangeRateCurrent"]); rate=int(er,10)/1e18; print("exchangeRateCurrent:", rate)
ab=ceth_call(SEL["accrualBlockNumber"]); print("accrualBlockNumber:", int(ab,16))
sr=ceth_call(SEL["supplyRatePerBlock"]); sri=int(sr,10); print("supplyRatePerBlock:", sri, "= 1e18-scaled ETH-per-block per ETH-supplied")
# daily interest across supply if accrued every block (upper bound; actual accrual is event-driven)
daily_eth=sri/1e18*86400*supply/1e8
print(f"implied interest/day at full accrual: {daily_eth:.4f} ETH; census measured 0.0136 ETH/day")
print("holder yield/day (interest share per supplied ETH):", sri/1e18*86400, "= ETH per ETH per day")
for tag in [26365189,26365190,26365191,26366000]:
    r=ceth_call(SEL["balanceOf"],"0x"+RECIPIENT[2:],hex(tag))
    print(f"balanceOf @{tag}:", int(r,16)/1e8 if r not in (None,"0x") else r)
