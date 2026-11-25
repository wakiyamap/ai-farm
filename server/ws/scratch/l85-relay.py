import json, urllib.request, sys
RELAY="http://127.0.0.1:8545"
CETH="0x4ddc2d193aaf8ce8c9ceb5ed6bd6ee6ef4190e6e"
RECIPIENT="0x8f10b468b06c6fd214b65f87778827f7d113f996"
SEL={"totalSupply":"0x18160ddd","balanceOf":"0x70a08231","exchangeRateCurrent":"0xbd6d894d","accrualBlockNumber":"0x6c540baf","supplyRatePerBlock":"0xae9d70b0"}
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(RELAY+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=60).read())
    if "error" in r: print("ERR", method, json.dumps(r["error"])); sys.exit(1)
    return r["result"]
def ceth_call(sig, extra="", tag="latest"):
    return rpc("eth_call",[{"to":CETH,"data":sig+extra}, tag])
ts=ceth_call(SEL["totalSupply"]); print("totalSupply:", int(ts,16)/1e8, "cETH units")
er=ceth_call(SEL["exchangeRateCurrent"]); print("exchangeRateCurrent:", int(er,10)/1e18)
ab=ceth_call(SEL["accrualBlockNumber"]); print("accrualBlockNumber:", int(ab,16))
sr=ceth_call(SEL["supplyRatePerBlock"]); sri=int(sr,10); print("supplyRatePerBlock:", sri)
blocks24h=144*7  # rate growth per day if every block accrued
print("implied daily rate growth (per-day rate x supply/1e8):", sri*86400/1e18*1e18/1e8, "ETH-day per cETH unit? units")
for tag in [26365189,26365190,26365191,26366000]:
    r=ceth_call(SEL["balanceOf"],"0x"+RECIPIENT[2:],hex(tag))
    print(f"balanceOf @{tag}:", int(r,16)/1e8 if r!="0x" else r)
