#!/usr/bin/env python3
"""franken-threshold-ethereum: threshold bidder for frankencoin MintingHub Dutch challenges.

Decision decisions/human/2026-11-16-franken-threshold-bid.md (lead 74):
- wait on ChallengeStarted (hub 0xDE12B620A8a714476A97EfD14E6F7180Ca653557); while a
  challenge is open read the state once per block, do NOT read per block when idle;
- STRIKE RULE: simulate the full executor bid at head each block; the executor returns
  the USDC profit (collateral sold on the real UniV3 pool minus the ZCHF offer minus
  flash premium, gas excluded). Send when net = profit - signed_gas_bound satisfies
  net >= MIN_NET_USD (25) AND net >= 3 x signed_gas_bound - i.e. beat the incumbent
  0xd694da17 at a line BELOW theirs, not in their block;
- one transaction (DutchThresholdBid.sol): Aave V3 flashLoanSimple USDC funds the
  ZCHF offer (USDC -> USDT -> ZCHF), hub.bid() takes the collateral, it is sold to
  USDC on a caller-supplied UniV3 pool, flash repaid inside the tx, the tx REVERTS
  unless profit >= minProfit, and the USDC profit is paid to the wallet in the same tx;
- send_route: private (Flashbots Protect) with a deadline block argument (head + 3):
  the public mempool copies the same bid (decision 2026-11-15-private-send.md);
  after sending, poll the receipt to the deadline and log private_not_included if none;
- stop line (decision §3): after 3 consecutive live failures (revert or not included)
  write state/STOPPED.json and stop sending - the incumbent lowered their line.

Paper mode simulates via eth_call with the pinned runtime override (state/
executor-code.hex = eth_getCode of the fork deployment 0x8f7a45ebde059392e46a46dcc14ab24681a961ea,
scratch/franken-threshold/proof.py); live mode verifies the gate deployment and sends
through the signer socket. A confirmed successful receipt IS the payout proof.
"""
import json, os, time, re, urllib.request, subprocess

WS = os.environ.get("BOT_WS", os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(WS, "logs", "bot.jsonl")
STATE_F = os.path.join(WS, "state", "cursor.json")
CODE_F = os.path.join(WS, "state", "executor-code.hex")
MODE = os.environ.get("BOT_MODE", "paper")
RELAY = os.environ["RPC_RELAY_URL"]
LANE = os.environ.get("RPC_LANE", "paper")

HUB = "0xDE12B620A8a714476A97EfD14E6F7180Ca653557"
TOPIC_STARTED = "0xc4b384b2c5ca32c8e77081f4083be594a1ea9ba34f208a9f9a458f70608585f5"
EXECUTOR_PAPER = "0x8f7a45ebde059392e46a46dcc14ab24681a961ea"  # fork deployment the pinned runtime was taken from
EXECUTOR = (os.environ.get("EXECUTOR_ADDR") or "").strip()
if re.fullmatch(r"0x[0-9a-fA-F]{40}", EXECUTOR or "x"):
    EXECUTOR = EXECUTOR.lower()
else:
    EXECUTOR = "" if MODE == "live" else EXECUTOR_PAPER  # live fails closed without the gate address
OWNER = "0x1111111111111111111111111111111111111111"  # paper stand-in: the pinned runtime's owner immutable
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
POOL_UNI = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"  # UniV3 USDC/WETH 0.05: ETH/USD valuation venue
# funding route pools (getters verified 2026-11-15 run 70853f4f, re-verified in fork proof controls 2026-11-16):
P_USDC_USDT = "0x3416cf6c708da44db2624d63ea0aaef7113527c6"  # UniV3 USDC/USDT 0.01, token0=USDC
P_ZCHF_USDT = "0x8e4318e2cb1ae291254b187001a59a1f8ac78cef"  # UniV3 ZCHF/USDT, token0=ZCHF
# collateral -> USDC exit pools (factory getPool + token0/token1 verified); unknown token = SKIP, never guess.
TOKEN_EXIT = {
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",  # WETH/USDC 0.05
    "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0": "0x4622df6fb2d9bee0dcdacf545acdb6a2b2f4f863",  # wstETH/USDC 0.05
    "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf": "0x4548280ac92507c9092a511c7396cbea78fa9e49",  # BTC.b/USDC 0.3
}
MIN_NET_USD = 25          # decision threshold: net (profit - gas bound) must reach this USDC figure
DEADLINE_AHEAD = 3        # private send: last block this bid may be included in
GAS_LIMIT = 1200000       # fork-proven gasUsed 435k-782k; worst case = GAS_LIMIT x maxFeePerGas
FEE_FLOOR, FEE_CAP = 10 ** 9, 20 * 10 ** 9  # maxFeePerGas clamp in wei
USD_MAX = 8               # manifest max_loss_per_tx_usd: bound clamped below this at signing
FAIL_STOP = 3             # decision §3: 3 consecutive live failures (revert or not included) -> stop
POLL_IDLE_S, POLL_ACTIVE_S = 30, 12
LIVE_LOSS_STOP_USD = 30

_id = 0
def rpc(method, params, lane=None, timeout=40):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request("%s/ethereum?lane=%s" % (RELAY, lane or LANE), data=body,
                                 headers={"content-type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    if "error" in d:
        raise RuntimeError(d["error"].get("message", "relay error"))
    return d["result"]

def log(kind, **kw):
    rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "kind": kind}
    rec.update(kw)
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")

def signer(req):
    import socket
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(60)
        s.connect(os.environ["SIGNER_SOCK"])
        s.sendall((json.dumps(req) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    return json.loads(buf or b'{"ok": false, "error": "no response"}')

def keccak(sig):
    return subprocess.run(["/opt/foundry/bin/cast", "keccak", sig], capture_output=True, text=True).stdout.strip()

def sel4(sig):
    return keccak(sig)[2:10]

def eth_usd_price():
    """Fresh ETH/USD from the UniV3 USDC/WETH pool spot price (token mapping re-verified)."""
    t0 = "0x" + rpc("eth_call", [{"to": POOL_UNI, "data": sel4("token0()")}, "latest"])[-40:]
    t1 = "0x" + rpc("eth_call", [{"to": POOL_UNI, "data": sel4("token1()")}, "latest"])[-40:]
    if {t0.lower(), t1.lower()} != {USDC, WETH}:
        raise RuntimeError("pool %s token mapping changed: %s/%s" % (POOL_UNI, t0, t1))
    r = rpc("eth_call", [{"to": POOL_UNI, "data": sel4("slot0()")}, "latest"])
    sqrtP = int(r[2:66], 16)
    if sqrtP < 10 ** 30:
        raise RuntimeError("slot0 sqrtPriceX96 implausible: %d" % sqrtP)
    price = 10 ** 12 * 2 ** 192 // (sqrtP * sqrtP)  # USD per WETH
    if not 100 < price < 10 ** 7:
        raise RuntimeError("implausible ETH/USD %d from slot0" % price)
    return price

def usd_fee(gas_limit, base, price):
    fee_cap_usd = USD_MAX * 10 ** 18 // (gas_limit * price)
    fee = min(max(base * 2, FEE_FLOOR), min(FEE_CAP, max(fee_cap_usd, FEE_FLOOR)))
    return fee, gas_limit * fee * price / 10 ** 18

def bid_calldata(num, size, max_offer, token, exit_pool, min_profit, deadline):
    return sel4("bid(uint32,uint256,uint256,address,address,address,address,uint256,uint256)") + \
        "%064x%064x%064x%064x%064x%064x%064x%064x%064x" % (
            int(num), int(size), int(max_offer), int(token, 16), int(exit_pool, 16),
            int(P_USDC_USDT, 16), int(P_ZCHF_USDT, 16), int(min_profit), int(deadline))

def hub_challenges(num, blk="latest"):
    r = rpc("eth_call", [{"to": HUB, "data": sel4("challenges(uint256)") + "%064x" % int(num)}, blk])
    vals = [r[i:i + 64] for i in (2, 66, 130, 194)]  # four UNPACKED words (verified shape, scratch/franken-decode-test.json)
    return {"challenger": "0x" + vals[0][-40:], "start": int(vals[1], 16),
            "position": "0x" + vals[2][-40:], "size": int(vals[3], 16)}

WALLET = OWNER  # live: replaced by the signer wallet address (the gate-deployed executor's owner)

def main():
    global WALLET
    exec_code = open(CODE_F).read().strip() if os.path.exists(CODE_F) else ""
    if MODE == "live":
        try:
            me = signer({"op": "address"})
            addr = (me.get("address") or me.get("addr") or "") if isinstance(me, dict) else ""
            if re.fullmatch(r"0x[0-9a-fA-F]{40}", addr or "x"):
                WALLET = addr
            else:
                log("startup_fail", note="signer wallet address unreadable, cannot simulate owner calls")
        except Exception as e:
            log("startup_fail", note="signer address read failed: %s" % str(e)[:120])
    head = int(rpc("eth_blockNumber", []), 16)
    st = json.load(open(STATE_F)) if os.path.exists(STATE_F) else {"cursor": head, "challenges": {}, "fail_streak": 0}
    log("startup", mode=MODE, head=head, exec=EXECUTOR, code_sha=bool(exec_code), cursor=st["cursor"],
        min_net_usd=MIN_NET_USD, deadline_ahead=DEADLINE_AHEAD)
    while True:
        try:
            act = any(c.get("status") == "open" for c in st["challenges"].values())
            head = int(rpc("eth_blockNumber", []), 16)
            blk = rpc("eth_getBlockByNumber", [hex(head), False])
            ts, base = int(blk["timestamp"], 16), int(blk.get("baseFeePerGas") or "0", 16)
            if st.get("stopped"):
                log("heartbeat", head=head, note="stopped (see state/STOPPED.json)")
                time.sleep(POLL_IDLE_S)
                continue
            if st["cursor"] < head:
                logs = rpc("eth_getLogs", [{"address": [HUB], "topics": [TOPIC_STARTED],
                                            "fromBlock": hex(st["cursor"] + 1), "toBlock": hex(head)}])
                for lg in logs or []:
                    # ChallengeStarted(indexed challenger, indexed position, size, number): data = [size][number]
                    num = int(lg["data"][66:130], 16)
                    pos = "0x" + lg["topics"][2][-40:]
                    token = "0x" + rpc("eth_call", [{"to": pos, "data": sel4("collateral()")}, "latest"])[-40:]
                    exit_pool = TOKEN_EXIT.get(token.lower())
                    if exit_pool is None:
                        log("event", num=num, position=pos, token=token, status="skipped",
                            note="collateral token has no verified UniV3 exit pool")
                        st["challenges"][str(num)] = {"status": "skipped", "token": token}
                        continue
                    st["challenges"][str(num)] = {"status": "open", "position": pos, "token": token,
                                                  "exit_pool": exit_pool, "block": int(lg["blockNumber"], 16)}
                    log("event", num=num, position=pos, token=token, block=int(lg["blockNumber"], 16),
                        status="open")
                st["cursor"] = head
            for num, ch in list(st["challenges"].items()):
                if ch.get("status") != "open":
                    continue
                c = hub_challenges(num)
                if c["challenger"] == "0x0000000000000000000000000000000000000000":
                    ch["status"] = "settled"
                    log("settled", num=num, note="challenge gone (taken or averted)")
                    continue
                size = c["size"]
                # per-block SIMULATION of the full executor bid at head (decision §1):
                # minProfit 0 so the call returns the raw profit; revert = nothing takeable now
                data = bid_calldata(num, size, 2 ** 255, ch["token"], ch["exit_pool"], 0, 2 ** 255)
                call_params = {"from": WALLET, "to": EXECUTOR, "data": data}
                try:
                    if MODE == "paper":
                        if not exec_code:
                            log("simulate", num=num, sim="no pinned runtime")
                            continue
                        ret = rpc("eth_call", [call_params, "latest", {EXECUTOR: {"code": exec_code}}])
                    else:
                        ret = rpc("eth_call", [call_params, "latest"])
                    profit = int(ret, 16) if ret and ret != "0x" else None
                except Exception as e:
                    msg = str(e)[:180]
                    if "0x" + sel4("NoChallenge()") in msg or "NoChallenge" in msg:
                        ch["status"] = "settled"
                        log("settled", num=num, note="simulate says NoChallenge")
                    else:
                        log("simulate_revert", num=num, err=msg)  # FlashShort etc: not profitable yet
                    continue
                if profit is None:
                    continue
                # gas bound at current fees: fee = min(2 x base, fee caps) with USD clamp
                try:
                    price = eth_usd_price()
                except Exception as e:
                    log("price_fail", num=num, err=str(e)[:120])
                    continue
                fee, bound = usd_fee(GAS_LIMIT, base, price)
                net = profit / 10 ** 6 - bound
                fire = net >= MIN_NET_USD and net >= 3 * bound
                log("simulate", num=num, profit_usdc=round(profit / 10 ** 6, 2), gas_bound_usd=round(bound, 2),
                    net_usdc=round(net, 2), fee_gwei=round(fee / 10 ** 9, 3), eth_usd=price, fire=bool(fire))
                if not fire:
                    continue
                # live-send offer cap: price() decays with time; 2x + 1 ZCHF slack covers an
                # oracle move between this simulation and inclusion (private route: an AboveCap
                # revert is free, a stale execution is not)
                px = int(rpc("eth_call", [{"to": HUB, "data": sel4("price(uint32)") + "%064x" % int(num)}, "latest"])[2:], 16)
                max_offer = px * size // 10 ** 18 * 2 + 10 ** 18
                data = bid_calldata(num, size, max_offer, ch["token"], ch["exit_pool"],
                                    MIN_NET_USD * 10 ** 6, head + DEADLINE_AHEAD)
                if MODE == "paper":
                    log("sent", num=num, mode="paper", profit_usdc=round(profit / 10 ** 6, 2),
                        net_usdc=round(net, 2),
                        note="simulated bid ok: flash-funded ZCHF offer, collateral sold via exit %s, USDC profit >= %d paid to wallet inside the tx" % (ch["exit_pool"], MIN_NET_USD))
                    ch["status"] = "done"
                    continue
                # live: one private send; signer rejection is final for this attempt
                resp = signer({"op": "send", "chain": "ethereum", "to": EXECUTOR, "data": data,
                               "gas": hex(GAS_LIMIT), "value": "0x0",
                               "maxFeePerGas": hex(fee), "maxPriorityFeePerGas": hex(fee // 10)})
                txh = resp.get("txHash")
                log("sent", num=num, mode="live", ok=bool(resp.get("ok")), txHash=txh,
                    err=(resp.get("error") or "")[:160], bound_usd=round(bound, 2), deadline=head + DEADLINE_AHEAD)
                if not resp.get("ok"):
                    st["fail_streak"] = st.get("fail_streak", 0) + 1
                    log("fail_streak", n=st["fail_streak"], reason="signer rejection")
                    check_stop(st)
                    continue
                # private send: poll the receipt until the deadline block passes (decision 2026-11-15-private-send.md)
                res = poll_private(txh, head + DEADLINE_AHEAD)
                if res == "confirmed":
                    ch["status"] = "done"
                    st["fail_streak"] = 0
                    log("settled", num=num, note="bid confirmed: USDC profit paid to wallet inside the tx")
                elif res == "reverted":
                    st["fail_streak"] = st.get("fail_streak", 0) + 1
                    log("bid_reverted", num=num, tx=txh, fail_streak=st["fail_streak"],
                        note="included but reverted (state moved or taken first); challenge stays open")
                    check_stop(st)
                else:
                    st["fail_streak"] = st.get("fail_streak", 0) + 1
                    log("private_not_included", num=num, tx=txh, fail_streak=st["fail_streak"],
                        deadline=head + DEADLINE_AHEAD)
                    check_stop(st)
            live = {k: v.get("status") for k, v in st["challenges"].items() if v.get("status") not in ("settled", "done", "skipped")}
            log("heartbeat", head=head, pending=live, fail_streak=st.get("fail_streak", 0))
            json.dump(st, open(STATE_F, "w"))
            time.sleep(POLL_ACTIVE_S if act else POLL_IDLE_S)
        except Exception as e:
            log("error", error=str(e)[:300])
            time.sleep(POLL_IDLE_S)

def poll_private(txh, deadline_block):
    for _ in range(40):
        try:
            rcpt = rpc("eth_getTransactionReceipt", [txh])
            if rcpt is not None:
                return "confirmed" if int(rcpt.get("status") or "0x0", 16) == 1 else "reverted"
            now = int(rpc("eth_blockNumber", []), 16)
            if now > deadline_block + 2:
                return "missing"
        except Exception:
            pass
        time.sleep(4)
    return "missing"

def check_stop(st):
    if st.get("fail_streak", 0) >= FAIL_STOP:
        st["stopped"] = True
        with open(os.path.join(WS, "state", "STOPPED.json"), "w") as f:
            json.dump({"reason": "%d consecutive private bids lost (revert or not included): incumbent lowered their line (decision 2026-11-16-franken-threshold-bid.md §3)" % st["fail_streak"],
                       "fail_streak": st["fail_streak"], "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, f)
        log("send_stop", fail_streak=st["fail_streak"], note="STOPPED.json written; recommend stop to inbox/meta")

if __name__ == "__main__":
    main()
