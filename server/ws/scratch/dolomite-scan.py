#!/usr/bin/env python3
# Dolomite LogLiquidate cadence scan through the RPC relay.
import json, os, sys, urllib.request

RELAY = os.environ["RPC_RELAY_URL"]
LANE = "research"
TOPIC0 = "0x1b9e65b359b871d74b1af1fc8b13b11635bfb097c4631b091eb762fda7e67dc7"
ADDRS = {
    "ethereum": "0x003Ca23Fd5F0ca87D01F6eC6CD14A8AE60c2b97D",
    "arbitrum": "0x6Bd780E7fDf01D77e4d475c821f1e7AE05409072",
}

def rpc(chain, method, params, cid):
    body = {"jsonrpc": "2.0", "id": cid, "method": method, "params": params}
    r = urllib.request.urlopen(
        urllib.request.Request(f"{RELAY}/{chain}?lane={LANE}",
                               data=json.dumps(body).encode(),
                               headers={"content-type": "application/json"}), timeout=60)
    return json.loads(r.read())["result"]

def scan(chain, nblocks):
    head = int(rpc(chain, "eth_blockNumber", [], 1), 16)
    out = []
    step = 50000
    start = head - nblocks
    cid = 10
    b = start
    while b < head:
        e = min(b + step, head)
        res = rpc(chain, "eth_getLogs", [{
            "fromBlock": hex(b), "toBlock": hex(e),
            "address": ADDRS[chain], "topics": [TOPIC0]}], cid)
        if res is None:
            print(f"{chain} {b}-{e}: result null", file=sys.stderr)
            res = []
        out.extend(res)
        b = e
        cid += 1
    return out, head

def main():
    plan = {"ethereum": 100000, "arbitrum": 400000}
    all = {}
    for chain, nb in plan.items():
        logs, head = scan(chain, nb)
        all[chain] = {"head": head, "nblocks": nb, "logs": logs}
        print(chain, "events:", len(logs), "head:", head, "window blocks:", nb)
        # decode scale: data = ABI-encoded 4 tuples; each BalanceUpdate = (deltaWei(Wei=(bool,uint256)), newPar(Par=(bool,uint128)))
        for lg in logs[:50]:
            d = lg["data"]
            w = lambda i: int.from_bytes(bytes.fromhex(d[2 + i * 64: 2 + (i + 1) * 64]), "big")
            # non-indexed words: solidHeld.deltaWei.sign, .value, newPar.sign, .value, solidOwed..., liquidHeld..., liquidOwed...
            owed = w(19)   # liquidOwedUpdate.deltaWei.value (debt assumed by liquidator)
            held = w(13)   # liquidHeldUpdate.deltaWei.value (collateral seized delta)
            print(chain, "blk", int(lg["blockNumber"], 16), "owedDelta", owed, "heldDelta", held,
                  "tx", lg["transactionHash"])
    json.dump(all, open("scratch/dolomite-logs.json", "w"))

main()
