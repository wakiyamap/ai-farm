#!/usr/bin/env python3
"""compound-accrue-ethereum SUCCESS-leg fork proof (run 602d1d015ddd49da81c09fea9ca1c56b).

Why: fork resets one block before a payout accrue pay 0 because the utilization
freshness that makes the payout positive is written in the same block before the
payout tx (manifest 2026-11-08). This script therefore resets the ethereum fork to
26365771, REPLAYS the 70 same-block predecessor transactions of the winner
0x92a8bceca4ea4563172f6c97de4c5af928f88f6a7766cc147386da50c0b9cfcb (block 26365772,
index 70; paid 0.021534003934147722 ETH to its sender), then deploys the AccrueKeeper
artifact with owner 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266 and calls
accrue(cETH, mantissa 45117721, minProfit 0.0002 ETH) from the owner account.
Success requires receipt status 1 AND a positive owner ETH balance delta (payout
minus the sender's gas). Run it under `fork lease ethereum 15` in one go and
`fork release` as it exits; the reviewer can rerun it.

Usage: fork lease ethereum 15 compound-accrue-proof && python3 scratch/compound-accrue-success-proof.py && fork release ethereum
"""
import json, os, sys, time, urllib.request, subprocess

FORK = "http://127.0.0.1:9003"
RELAY = os.environ["RPC_RELAY_URL"]
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
OWNER = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"  # funded fork account (anvil account 0)
RESET_BLOCK = 26365771
WINNER_BLOCK = 26365772
WINNER_HASH = "0x92a8bceca4ea4563172f6c97de4c5af928f88f6a7766cc147386da50c0b9cfcb"
MANTISSA = 45117721          # the internal accrueInterest mantissa the winner paid 0.0215 ETH with (trace of WINNER_HASH)
MIN_PROFIT = 2 * 10**14      # 0.0002 ETH (bot MIN_PROFIT_ETH)
GAS = 0x30D90                # 200000
ARTIFACT = "scratch/compound-accrue-ethereum/contracts/out/AccrueKeeper.sol/AccrueKeeper.json"
OUT = "scratch/compound-accrue-success-proof.json"


def rpc(url, method, params):
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    if "error" in d and d["error"]:
        raise RuntimeError(f"{method}: {str(d['error'])[:200]}")
    return d["result"]


def receipt(url, h, tries=30):
    for _ in range(tries):
        r = rpc(url, "eth_getTransactionReceipt", [h])
        if r:
            return r
        time.sleep(0.3)
    raise RuntimeError(f"no receipt for {h}")


def send(url, tx):
    h = rpc(url, "eth_sendTransaction", [tx])
    return receipt(url, h), h


def hexn(x):
    return int(x, 16) if isinstance(x, str) else x


def main():
    url = FORK
    # 1) reset (lease-guarded by the caller via the fork tool; the script reruns it identically)
    rpc(url, "anvil_reset", [{"forking": {"jsonRpcUrl": f"{RELAY}/ethereum?lane=research", "blockNumber": RESET_BLOCK}}])
    head0 = hexn(rpc(url, "eth_blockNumber", []))
    # 1b) pace the fork blocks at mainnet block time. The migrated cETH accrue
    #     payout is timestamp-driven: with real-time fork blocks the payout is ~0
    #     even though the fork prestate equals the mainnet payout-tx prestate
    #     (measured: all cETH storage slots identical). Progress-mode time from
    #     the reset block timestamp at 12 s/block makes the accrue call see the
    #     same accrual-clock seconds gap the mainnet payout tx saw (within ~4%).
    blk_pre = rpc(f"{RELAY}/ethereum?lane=research", "eth_getBlockByNumber", [hex(RESET_BLOCK), False])
    ts0 = hexn(blk_pre["timestamp"])
    pace = int(os.environ.get("PACE_OFFSET", "12"))
    # this anvil has no progress-mode setTime; setTime(ts) shifts the mined-block
    # clock so the next block starts at ts and later blocks advance from there.
    # The migrated cETH accrue payout is seconds-gap driven: with real-time fork
    # blocks (3.6-day accrual gap) the payout collapses ~6448x (measured: the
    # mainnet winner's own replay on the fork paid its helper 3.34e12 wei vs
    # 2.1534e16 on mainnet). PACE_OFFSET shifts the fork clock base so the
    # accrue call sees a chosen seconds gap (PACE_OFFSET=300000 tests the
    # payout's proportionality to the gap).
    rpc(url, "anvil_setTime", [hex(ts0 + pace)])
    # 2) fetch the winner block from the relay and replay its predecessors
    blk = rpc(f"{RELAY}/ethereum?lane=research", "eth_getBlockByNumber", [hex(WINNER_BLOCK), True])
    txs = blk["transactions"]
    idx = [i for i, t in enumerate(txs) if t["hash"] == WINNER_HASH]
    if not idx:
        raise RuntimeError("winner tx not in block")
    i = idx[0]
    pre = txs[:i]
    replay = []
    for t in pre:
        tx = {"from": t["from"], "to": t.get("to"), "input": t.get("input") or "0x",
              "value": t["value"], "gas": t["gas"], "nonce": t["nonce"]}
        # the relay result carries BOTH a computed gasPrice and the EIP-1559 fee
        # fields for 1559 txs; anvil rejects the mix - pass one family only.
        if t.get("maxFeePerGas"):
            for k in ("maxFeePerGas", "maxPriorityFeePerGas"):
                if t.get(k):
                    tx[k] = t[k]
            tx["type"] = t.get("type", "0x2")
        elif t.get("gasPrice"):
            tx["gasPrice"] = t["gasPrice"]
        try:
            r, h = send(url, tx)
            replay.append({"hash": h, "status": r["status"], "gasUsed": hexn(r["gasUsed"]),
                           "from": t["from"], "to": t.get("to"), "sel": (t.get("input") or "0x")[:10]})
        except Exception as e:
            replay.append({"hash": None, "error": str(e)[:120], "from": t["from"], "to": t.get("to")})
    ok_pre = sum(1 for r in replay if r.get("status") == "0x1")
    head1 = hexn(rpc(url, "eth_blockNumber", []))
    # 3) deploy the AccrueKeeper with constructor(address owner, uint256 minProfitCap)
    args = "0x" + OWNER[2:].rjust(64, "0") + format(10**16, "064x")
    out = subprocess.run(["fork", "deploy", "ethereum", ARTIFACT, "--args", args],
                         capture_output=True, text=True)
    deployed = out.stdout.strip().split("\n")[-1]
    if out.returncode or not deployed.startswith("0x") or len(deployed) != 42:
        raise RuntimeError(f"deploy failed: {out.stdout[-300:]} {out.stderr[-300:]}")
    # 4) fund the owner (gas for the call) and record its balance
    rpc(url, "anvil_setBalance", [OWNER, hex(10**18)])
    bal0 = hexn(rpc(url, "eth_getBalance", [OWNER, "latest"]))
    # 5) call accrue(cETH, mantissa, minProfit)
    data = "0x037b1e29" + CETH[2:].rjust(64, "0") + format(MANTISSA, "064x") + format(MIN_PROFIT, "064x")
    r, h = send(url, {"from": OWNER, "to": deployed, "data": data, "gas": hex(GAS)})
    status = r["status"]
    bal1 = hexn(rpc(url, "eth_getBalance", [OWNER, "latest"]))
    reason = None
    if status != "0x1":
        try:
            reason = rpc(url, "eth_call", [{"from": OWNER, "to": deployed, "data": data, "value": "0x0"}, "latest"])
        except Exception as e:
            reason = str(e)[:160]
    # accrual-clock seconds gap the call saw (for the record; the mainnet payout tx
    # saw the same gap its block timestamp minus the accrualBlockNumber block timestamp)
    ab = hexn(rpc(url, "eth_call", [{"to": CETH, "data": "0x6c540baf"}, "latest"]))
    ts_ab = hexn(rpc(f"{RELAY}/ethereum?lane=research", "eth_getBlockByNumber", [hex(ab), False])["timestamp"])
    blk_call = rpc(url, "eth_getBlockByNumber", [hex(hexn(r["blockNumber"])), False])
    gap_seconds_call = hexn(blk_call["timestamp"]) - ts_ab
    # 6) replay the mainnet payout tx itself on the same paced fork and watch its
    #    helper recipient's ETH delta: proves whether the payout mechanism's scale
    #    reproduces (helper path) alongside the executor's redeem(mantissa) path.
    winner = rpc(f"{RELAY}/ethereum?lane=research", "eth_getTransactionByHash", [WINNER_HASH])
    helper = winner["to"]
    rpc(url, "anvil_setBalance", [winner["from"], hex(10**18)])
    hb0 = hexn(rpc(url, "eth_getBalance", [helper, "latest"]))
    wt = {"from": winner["from"], "to": winner["to"], "input": winner["input"],
          "value": winner["value"], "gas": winner["gas"], "nonce": winner["nonce"]}
    for k in ("maxFeePerGas", "maxPriorityFeePerGas"):
        if winner.get(k):
            wt[k] = winner[k]
    rw, hw = send(url, wt)
    hb1 = hexn(rpc(url, "eth_getBalance", [helper, "latest"]))
    result = {
        "reset_block": RESET_BLOCK,
        "predecessors_replayed": len(pre),
        "predecessors_ok": ok_pre,
        "fork_head_before_call": head1,
        "deployed": deployed,
        "deploy_tx": out.stdout.strip().split("\n")[0],
        "accrue_tx": h,
        "accrue_status": status,
        "accrue_gasUsed": hexn(r["gasUsed"]),
        "accrue_revert_reason": reason,
        "owner": OWNER,
        "owner_balance_before": bal0,
        "owner_balance_after": bal1,
        "owner_delta_eth": (bal1 - bal0) / 1e18,
        "mantissa": MANTISSA,
        "min_profit": MIN_PROFIT,
        "head0": head0,
        "reset_ts0": ts0,
        "pace_offset": pace,
        "gap_seconds_call": gap_seconds_call,
        "mainnet_winner_gap_seconds": hexn(blk["timestamp"]) - ts_ab,
        "winner_replay_tx": hw,
        "winner_replay_status": rw["status"],
        "winner_helper_delta_wei": hb1 - hb0,
        "mainnet_helper_payout_wei": 21534003934147722,
        "success_leg": status == "0x1" and bal1 > bal0,
        "replay": replay,
    }
    json.dump(result, open(OUT, "w"), indent=1)
    print(json.dumps({k: v for k, v in result.items() if k != "replay"}, indent=1))
    if result["success_leg"]:
        print(f"SUCCESS LEG: accrue tx {h} paid owner {result['owner_delta_eth']} ETH net of gas")
    else:
        print("success leg NOT reproduced:", reason)
        sys.exit(2)


if __name__ == "__main__":
    main()
