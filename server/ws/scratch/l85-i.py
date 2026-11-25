import json, urllib.request, sys
RELAY="http://127.0.0.1:8545"
CETH="0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
REC="0x8f10b468b06c6fd214b65f87778827f7d113f996"
REC2="0x60b0f1919cf4ee46d1a8d63428276512814de570"
def rpc(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(RELAY+"/ethereum?lane=research", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in r: print("ERR", method, json.dumps(r["error"])[:100]); return None
    return r["result"]
def h(x): return None if x in (None,"0x") else int(x,16)
def call(sig, extra="", tag="latest"):
    return rpc("eth_call",[{"to":CETH,"data":sig+extra}, tag])
print("symbol:", bytes.fromhex((call("0x95d89b41") or "0x")[66:]).decode() if call("0x95d89b41") else None)
sup=h(call("0x18160ddd")); rate=h(call("0xbd6d894d"))/1e10
srb=h(call("0xae9d70b0")); brb=h(call("0xc39f0594"))
print(f"cETH totalSupply={sup/1e8:.1f} units, exchangeRate={rate:.10f} ETH/unit")
print(f"supplyRatePerBlock={srb}, borrowRatePerBlock={brb}")
if sup and rate:
    eth_sup=sup/1e8*rate
    print(f"underlying ETH supply≈{eth_sup:.1f} ETH (~{eth_sup*2234:.0f} USD at 2234)")
    # interest/day upper bound if accrued every block:
    daily=srb/1e18*86400*sup/1e8*rate  # ETH/day? srb is per-supplied-ETH fraction; interest accrues on borrows: srb*supply in ETH
    print(f"interest/day at full accrual≈{daily:.4f} ETH/day (~{daily*2234:.1f} USD/day) across whole market")
    for tag,who in [("latest",REC),("latest",REC2),(hex(26365189),REC),(hex(26365190),REC),(hex(26365191),REC)]:
        b=h(call("0x70a08231",who[2:],tag))
        print(f"cETH balanceOf {who[:6]}… @{tag}: {b/1e8 if b is not None else b}")
