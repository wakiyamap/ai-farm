#!/usr/bin/env python3
"""Gearbox V3 live-state poll probe (earner run ec9955a8, 2026-11-07).
Checks the poller path on mainnet latest: creditManager discovery, account pages,
isLiquidatable sweep. Writes scratch/gb-live-probe.json."""
import json, urllib.request, os

RELAY = os.environ.get("RPC_RELAY_URL", "http://127.0.0.1:8545")
LANE = "research"
_id = [0]

def rpc(method, params, lane=None):
    _id[0] += 1
    url = f"{RELAY}/ethereum?lane={lane or LANE}"
    body = json.dumps({"jsonrpc":"2.0","id":_id[0],"method":method,"params":params}).encode()
    req = urllib.request.Request(url, data=body, headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    if "error" in r: raise RuntimeError(f"{method}: {r['error']}")
    return r["result"]

def word(x):
    if isinstance(x, int): return format(x,"x").rjust(64,"0")
    return x[2:].lower().rjust(64,"0")

FACADE="0x4da50da058ad6cc96bb63edff55b534d2a2cbe92"
COMPRESSOR="0x81cb9eA2d59414Ab13ec0567EFB09767Ddbe897a"
S_CMANAGER="0xc12c21c0"; S_GETACCTS="0x3b007fb9"; S_ISLIQ="0x8340e24d"
S_UND="0x6f307dc3"

out={}
out["latest_block"]=int(rpc("eth_blockNumber",[]),16)
cm="0x"+rpc("eth_call",[{"to":FACADE,"data":S_CMANAGER},"latest"])[-40:]
und="0x"+rpc("eth_call",[{"to":FACADE,"data":S_UND},"latest"])[-40:]
out["credit_manager"],out["underlying"]=cm,und
accounts=[]
for off in range(0,400,100):
    page=rpc("eth_call",[{"to":COMPRESSOR,"data":S_GETACCTS+word(cm)+word(off)+word(100)},"latest"])
    body=page[2:]; n=int(body[:64],16)
    accounts+= ["0x"+body[64+i*64:128+i*64][-40:] for i in range(n)]
    if n<100: break
out["accounts_n"]=len(accounts)
liq=[]
errors=0
for a in accounts:
    try:
        v=int(rpc("eth_call",[{"to":cm,"data":S_ISLIQ+word(a)+word(10000)},"latest"]),16)
        if v==1: liq.append(a)
    except RuntimeError as e:
        errors+=1
out["liquidatable"]=liq; out["isliq_errors"]=errors
# for each liquidatable account, WMoo balance + underlying debt via cm.getCreditAccount? use balanceOf WMoo
WMOO="0x1a711a5bc48b5c1352c1882fa65dc14b5b9e829d"; WETH="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
S_BALOF="0x70a08231"
details={}
for a in liq[:5]:
    bal_w=int(rpc("eth_call",[{"to":WETH,"data":S_BALOF+word(a)},"latest"]),16)
    details[a]={"weth_bal":bal_w/1e18}
out["liq_details"]=details
json.dump(out,open("scratch/gb-live-probe.json","w"),indent=1)
print(json.dumps(out,indent=1))
