#!/usr/bin/env python3
"""Real-chain: incumbent Mint txs on pool 0x9779... -> pin the liquidity param scale.
Compare tx input liquidity param (word4) vs event data.amount (liquidity minted)
vs pool liquidity() before/after the tx block."""
import json, sys, urllib.request as U
REL = "http://127.0.0.1:8545/elysium?lane=research"
POOL = "0x97796d80b6a1db78632f7451196b04f307329eb6"
MINT_T0 = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
def rpc(method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    r = json.loads(U.urlopen(U.Request(REL, data=body, headers={"content-type":"application/json"}), timeout=60).read())
    if "error" in r: print("ERR", method, json.dumps(r["error"])[:200]); sys.exit(1)
    return r["result"]
def i(x): return int.from_bytes(bytes.fromhex(x[2:]),"big") if x and x!="0x" else 0
head = int(rpc("eth_blockNumber",[]),16)
print("head", head)
logs = rpc("eth_getLogs",[{"address":POOL,"topics":[MINT_T0],"fromBlock":hex(head-9000),"toBlock":hex(head)}])
print("Mint logs in last 9000 blocks:", len(logs))
for lg in logs[:4]:
    th = lg["transactionHash"]; bn = int(lg["blockNumber"],16)
    topics = lg["topics"]; data = lg["data"]
    owner = topics[1][-40:]; lo = i(topics[2]); hi = i(topics[3])
    d = bytes.fromhex(data[2:])
    sender = "0x"+d[0:16].hex()[-20:]  # packable? sender may be last bytes of a 32B word; handle both
    amount = int.from_bytes(d[16:32],"big"); a0 = int.from_bytes(d[32:64],"big"); a1 = int.from_bytes(d[64:96],"big")
    amount_alt = int.from_bytes(d[0:16],"big")  # if data[0:16] is amount instead
    tx = rpc("eth_getTransactionByHash",[th])
    inp = tx["input"]
    params = [inp[j*64+24:(j+1)*64+24] for j in range(1,5)]
    p_liquidity = int.from_bytes(bytes.fromhex(inp[4+3*64+2:4+4*64+2])[-16:] if False else bytes.fromhex(inp[196:228]),"big")
    liq_before = i(rpc("eth_call",[{"to":POOL,"data":"0x1a686502"},hex(bn-1)]))
    liq_after  = i(rpc("eth_call",[{"to":POOL,"data":"0x1a686502"},hex(bn)]))
    print(f"tx {th[:14]}... blk {bn} owner {owner[-8:]} ticks {lo}..{hi}")
    print(f"  data.amount(word16:32)={amount} alt(word0:16)={amount_alt} amount0={a0} amount1={a1}")
    print(f"  input liquidity param = {p_liquidity}  input len {len(inp)//2} B")
    print(f"  pool liquidity before/after = {liq_before} -> {liq_after}  delta {liq_after-liq_before}")
    print(f"  ratio param/delta = {p_liquidity/max(liq_after-liq_before,1):.4g}  event.amount {amount} vs delta {liq_after-liq_before}")
