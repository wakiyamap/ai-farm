"""Run 8980b787: defi.money PegKeeperRegulator state on one chain: keepers, pools, coins, action delay,
estimate_caller_profit now, and a stranger eth_call of update(pk, beneficiary). Research lane, 0 fork, 0 tx.
usage: r8980-pk-state.py <chain> <regulator>"""
import json, os, subprocess, sys, urllib.request
chain, REG = sys.argv[1], sys.argv[2]
RELAY = os.environ["RPC_RELAY_URL"].rstrip("/") + f"/{chain}?lane=research"
CAST = "/opt/foundry/bin/cast"
STRANGER = "0x00000000000000000000000000000000000ca11e"

def cd(sig, *a):
    return subprocess.check_output([CAST, "calldata", sig, *[str(x) for x in a]], text=True).strip()

def rpc(m, p):
    req = urllib.request.Request(RELAY, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), {"content-type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def call(to, data, frm=None):
    tx = {"to": to, "data": data}
    if frm:
        tx["from"] = frm
    return rpc("eth_call", [tx, "latest"])

def dec(types, hexdata):
    return subprocess.check_output([CAST, "abi-decode", f"f()({types})", hexdata], text=True).strip().split("\n")

blk = rpc("eth_getBlockByNumber", ["latest", False])["result"]
now = int(blk["timestamp"], 16)
print("chain", chain, "block", int(blk["number"], 16), "ts", now)
delay = int(call(REG, cd("action_delay()"))["result"], 16)
print("action_delay", delay, "is_killed", call(REG, cd("is_killed()"))["result"][-2:],
      "oracle", "0x" + call(REG, cd("STABLECOIN_ORACLE()"))["result"][26:])
orc = "0x" + call(REG, cd("STABLECOIN_ORACLE()"))["result"][26:]
print("stable oracle price", int(call(orc, cd("price()"))["result"], 16) / 1e18)
out = {"chain": chain, "block": int(blk["number"], 16), "ts": now, "action_delay": delay, "keepers": []}
for i in range(8):
    r = call(REG, cd("peg_keepers(uint256)", i))
    if "error" in r or not r.get("result") or len(r["result"]) < 10:
        break
    w = r["result"][2:]
    pk, pool = "0x" + w[24:64], "0x" + w[88:128]
    inv, ceil, last = int(w[128:192], 16), int(w[192:256], 16), int(w[256:320], 16)
    coins = ["0x" + call(pool, cd("coins(uint256)", j))["result"][26:] for j in (0, 1)]
    syms = []
    for c in coins:
        s = call(c, "0x95d89b41").get("result", "0x")
        try:
            raw = bytes.fromhex(s[2:]); n = int.from_bytes(raw[32:64], "big"); syms.append(raw[64:64 + n].decode())
        except Exception:
            syms.append("?")
    bals = [int(call(pool, cd("balances(uint256)", j))["result"], 16) for j in (0, 1)]
    est = call(REG, cd("estimate_caller_profit(address)", pk))
    estv = int(est["result"], 16) if est.get("result") else None
    debt = int(call(pk, cd("debt()"))["result"], 16)
    share = int(call(pk, cd("caller_share()"))["result"], 16)
    vp = int(call(pool, cd("get_virtual_price()"))["result"], 16) / 1e18
    upd = call(REG, cd("update(address,address)", pk, STRANGER), STRANGER)
    res = ("ok caller_profit=%d" % int(upd["result"], 16)) if upd.get("result") else ("revert " + str(upd.get("error"))[:140])
    print(f"pk{i} {pk} pool {pool} {syms} bals {bals} inverse {inv} ceiling {ceil/1e18:.0f} debt {debt/1e18:.2f} share {share} vp {vp:.5f}")
    print(f"     last_change {last} ({now-last} s ago) estimate_caller_profit {estv} ({(estv or 0)/1e18:.6f} LP) stranger update: {res}")
    out["keepers"].append({"pk": pk, "pool": pool, "coins": coins, "syms": syms, "bals": bals, "ceiling": ceil, "debt": debt, "share": share,
                           "last_change": last, "est": estv, "stranger": res, "vp": vp})
json.dump(out, open(f"/srv/farm/ws/scratch/r8980-pk-state-{chain}.json", "w"), indent=1)
