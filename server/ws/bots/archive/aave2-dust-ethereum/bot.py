#!/usr/bin/env python3
"""aave2-dust-ethereum: aave v2 legacy pool dust batch-liquidation paper bot.

Discovers the dust cohort from fresh pool LiquidationCall events (incumbent
sweeps at 97 pct repayment reveal a liquidatable tail >=301 blocks before
capture), checks getUserAccountData health factor through the relay, and
simulates our executor contract liquidateBatch on CURRENT chain state
(relay eth_call with the executor runtime as a code override, per
wiki pitfalls/executor-paper-sim-override.md). Paper mode never sends; live
mode sends through the signer socket.
"""
import json
import os
import time
import urllib.request

POOL = "0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9"  # aave v2 LendingPool (measured, not memory)
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
STETH = "0xae7ab96520de3a18e5e111b5eaab095312d7fe84"
LIQ_TOPIC = "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"  # LiquidationCall(address indexed collateral, indexed liquidity, indexed user, uint256 dtc, uint256 liqCollateral, uint256 bonus)
EXECUTOR = os.environ.get("EXECUTOR", "0xace52ba533a494001bd523c29330e640bbb37ed7")
# LiquidationCall has THREE indexed fields: collateral, liquidityAsset, user -> user is
# topics[3] (topics[0] is the event hash); debtToCover is the FIRST word of data.
SIM_FROM = "0x0000000000000000000000000000000000000000"  # executor owner() reads as 0 on the placeholder
POLL_SECS = 60          # window is >=301 blocks: polling is fine, no latency race
MAX_BATCH = 32          # measured ~359k gas/liquidation -> 32 x 359k < 13M gasLimit
MIN_PROFIT = 10**11   # stETH 18-dec wei floor per batch: contract reverts NO_PROFIT unless the batch added >= minProfit stETH (measured bonus = 10 pct of debtToCover IN COLLATERAL, attempts 310: median batch-32 bonus ~3.6e14 wei stETH; 1e11 wei ~ 0.0002 USD)
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state", "state.json")
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "bot.jsonl")
GAS_LIMIT = 13_000_000  # 32 x measured 359k gas/liquidation <= 13M (manifest max_loss_guarantee)

RELAY = os.environ["RPC_RELAY_URL"] + "/ethereum?lane=" + os.environ.get("RPC_LANE", "paper")
FORK = os.environ.get("FORK_URL") or "http://127.0.0.1:9003"
MODE = os.environ.get("BOT_MODE", "paper")


def rpc(url, method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    j = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in j:
        raise RuntimeError(str(j["error"]))
    return j["result"]


def log(rec):
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), exist_ok=True)
    rec = dict(t=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), mode=MODE, **rec)
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")


def enc_batch(users, dtcs, min_profit):
    w = lambda x: f"{x:0>64x}"
    n = len(users)
    ptrs = w(0x60) + w(0x60 + 0x20 + 32 * n) + w(min_profit)
    body = w(n) + "".join("0" * 24 + u[2:] for u in users)
    body += w(n) + "".join(w(int(d)) for d in dtcs)
    return "0x32059dcf" + ptrs + body


def hf_of(result_hex):
    # getUserAccountData -> [availETH, totalCollateral, totalDebt, availableLiquidity, availableWithBonus, healthFactor] (18-dec)
    words = [result_hex[2 + 64 * i:66 + 64 * i] for i in range(len(result_hex[2:]) // 64)]
    if len(words) < 6:
        return None
    return int(words[5], 16) / 1e18


def executor_runtime():
    # re-take the runtime from the FORK instance after every source change (never forge's
    # deployedBytecode: immutables are zero placeholders in the artifact)
    return rpc(FORK, "eth_getCode", [EXECUTOR, "latest"])


def main():
    st = {"last_block": None, "pending": []}
    if os.path.exists(STATE):
        st = json.load(open(STATE))
    while True:
        try:
            head = int(rpc(RELAY, "eth_blockNumber", []), 16)
            if st["last_block"] is None:
                st["last_block"] = head - 300  # first run: scan last ~1 day
            scan_to = min(head - 1, st["last_block"] + 2000)
            new = []
            if scan_to > st["last_block"]:
                logs = rpc(RELAY, "eth_getLogs", [{
                    "address": POOL, "topics": [LIQ_TOPIC],
                    "fromBlock": hex(st["last_block"] + 1), "toBlock": hex(scan_to)}])
                # three indexed fields: collateral, liquidity, user -> user = topics[3];
                # debtToCover = first 32-byte word of the data field
                new = [{"block": int(l["blockNumber"], 16), "tx": l["transactionHash"],
                        "user": "0x" + l["topics"][3][40:], "dtc": int(l["data"][2:66], 16)}
                       for l in logs if len(l["topics"]) == 4 and len(l["data"]) >= 130]
            seen = {c["tx"] + c["user"] for c in st["pending"]}
            st["pending"] = st["pending"] + [c for c in new if (c["tx"] + c["user"]) not in seen]
            st["last_block"] = scan_to
            sim = None
            if st["pending"]:
                batch = st["pending"][:MAX_BATCH]
                users = [c["user"] for c in batch]
                dtcs = [c["dtc"] for c in batch]
                checks, liq = [], []
                for u in users[:5]:
                    try:
                        r = rpc(RELAY, "eth_call", [{"to": POOL, "from": SIM_FROM,
                                                      "data": "0xbf92857c" + u[2:]}, "latest"])
                        h = hf_of(r)
                        checks.append({"user": u, "hf": h})
                        if h is not None and h < 1.0:
                            liq.append(u)
                    except Exception as e:
                        checks.append({"user": u, "err": str(e)[:80]})
                # simulate the executor against CURRENT chain state: relay eth_call of the
                # executor address with its fork runtime as a code override
                try:
                    if MODE == "live":
                        live_code = rpc(RELAY, "eth_getCode", [EXECUTOR, "latest"])
                        if len(live_code) < 10:
                            raise RuntimeError("EXECUTOR_NOT_DEPLOYED_LIVE")
                        # the deployed executor restricts calls to its owner (the gate deployer);
                        # read owner() and simulate as the owner, not the zero placeholder
                        owner = "0x" + rpc(RELAY, "eth_call", [{"to": EXECUTOR,
                                                                 "data": "0x8da5cb5b"}, "latest"])[2:][-40:]
                        call = {"from": owner, "to": EXECUTOR,
                                "data": enc_batch(users, dtcs, MIN_PROFIT)}
                        sim_ok = rpc(RELAY, "eth_call", [call, "latest"])
                    else:
                        rt = executor_runtime()
                        if len(rt) < 10:
                            raise RuntimeError("EXECUTOR_NOT_DEPLOYED_ON_FORK")
                        call = {"from": SIM_FROM, "to": EXECUTOR, "code": rt,
                                "data": enc_batch(users, dtcs, MIN_PROFIT)}
                        sim_ok = rpc(RELAY, "eth_call", [call, "latest"])
                    sim = {"ok": True, "profit_steth_wei": int(sim_ok, 16)}
                except Exception as e:
                    sim = {"ok": False, "err": str(e)[:120]}
                log({"block": head, "found": len(new), "pending": len(st["pending"]),
                     "hf_checks": checks, "sim": sim})
                if sim.get("ok") and sim.get("profit_steth_wei", 0) >= MIN_PROFIT:
                    sent = None
                    if MODE == "live":
                        # one transaction through the deployed executor; the signer holds the key
                        import sys
                        sys.path.append("/opt/farm/lib")
                        import farmbot_signer
                        sent = farmbot_signer.send("ethereum", EXECUTOR,
                                                   data=enc_batch(users, dtcs, MIN_PROFIT),
                                                   gas=GAS_LIMIT)
                    st["pending"] = st["pending"][len(batch):]  # consumed batch (paper: no send)
                    log({"consumed": len(batch), "sent": sent})
            log({"beat": head, "pending": len(st["pending"])})
            os.makedirs(os.path.dirname(STATE), exist_ok=True)
            json.dump(st, open(STATE, "w"))
        except Exception as e:
            log({"error": str(e)[:200]})
        time.sleep(POLL_SECS)


main()
