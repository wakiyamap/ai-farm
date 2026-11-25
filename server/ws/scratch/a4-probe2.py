#!/usr/bin/env python3
"""Lead 67 decisive latency re-measurement (relay research lane).

Probe Spoke.liquidationCall(cR,dR,user,debtToCover=debt_captured,false) via eth_call at
block E-offset for each capture's own liquidator wallet. Decoding:
  revert 0x930bb771 = HealthFactorNotBelowThreshold  -> position HEALTHY at that block (not liquidatable)
  any other error   = HF check PASSED (deeper checks: ReserveNotSupplied 0xe2fadb09, ERC20, ...) -> liquidatable
Poll-catchable <=> liquidatable at E-1 (or earlier). Same-block race <=> healthy at E-1.
Controls from the earlier ladder (scratch/a4-window-probe.json): capture 26246672 reaches
ReserveNotSupplied at E-65536 (HF passed there) and capture 26352006 reverts an ERC20
balance error at E-1 (HF passed at E-1): proof the non-HF signal means liquidatable.
"""
import json, subprocess, sys

RELAY = "http://127.0.0.1:8545"
SPOKE = "0x973a023a77420ba610f06b3858ad991df6d85a08"
SEL = "0xc2fa746c"  # liquidationCall(uint256,uint256,address,uint256,bool)

def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    r = subprocess.run(["curl","-s","-m","25","-X",f"{RELAY}/ethereum?lane=research","-H","content-type: application/json","-d",body],
                       capture_output=True, text=True)
    resp = json.loads(r.stdout)
    if "error" in resp:
        print("RPCERR", json.dumps(resp["error"])[:200], file=sys.stderr)
        return None
    return resp["result"]

def probe(wallet, cR, dR, user, debt, block):
    data = SEL + hex(cR)[2:].rjust(64,"0") + hex(dR)[2:].rjust(64,"0") + user[2:].rjust(64,"0") + hex(debt)[2:].rjust(64,"0") + "0"*64
    res = rpc("eth_call", [{"from": wallet, "to": SPOKE, "data": data}, hex(block)])
    if res is None: return "rpcerr"
    if res == "0x" or not res.startswith("0x0"):  # success or non-error return
        return res[:10]
    return res[:10] if len(res) < 20 else "string-revert"  # custom errors are 4 bytes

# from scratch/a4-liq-decoded.json: (block, cR, dR, user, debtRaw, liquidator wallet)
CAPS = [
 (26198214, 1, 10, "0x45f9fa6099f798ba56a335408f178216753a9b72", 2119703139, "0xd12810b19b596347a3afac206d3ca65d08594b3f"),
 (26202470, 1,  4, "0x7c89042f6a564895f74225e66256627480330174", 6838825461, "0xd12810b19b596347a3afac206d3ca65d08594b3f"),
 (26215362, 0,  8, "0x2ab5a19adcaa55f256e5a3f6a490827404141913", 2063366036985913488, "0x00acd5002577625b008cf26f58f4c2a60c434cc9"),
 (26250655, 1,  5, "0xac90a9f2cf5636202919455f263746e5f98f937d", 33018055795, "0xb6fec1ab7f3e0d2a8b082dc06b9f7f8c8d618840"),
 (26263287, 0,  7, "0xe8e61c8207336326704817308a75e28638f9b3f6", 9163928602, "0xd12810b19b596347a3afac206d3ca65d08594b3f"),
 (26338631, 1,  4, "0x38e3842718730cc619f5c051c3e56cc77d962ce0", 6168864935, "0xd12810b19b596347a3afac206d380e4d650717"),
]
