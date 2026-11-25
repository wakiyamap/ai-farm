#!/usr/bin/env python3
"""franken-dutch-tail-ethereum: bid 6 chain-seconds BEFORE frankencoin MintingHub Dutch expiry (the -6s tail tweak of lead 74).

Polls ChallengeStarted logs on the hub; for each challenge it waits until
start + 2 * phase - 6 (the Dutch offer has decayed to a tiny precomputable value
there, attempts 1300/1308), then bids the full remaining size through the executor
(DutchFlashTail.sol) in ONE transaction: an Aave V3 flashLoanSimple of USDC funds
the ZCHF offer (USDC -> USDT -> ZCHF), hub.bid() delivers the collateral, the
collateral is sold to USDC on a caller-supplied UniV3 exit pool, the flash loan is
repaid inside executeOperation, and the tx REVERTS unless the executor's USDC ends
above borrow + premium + minProfit; the profit is then sent to the bot wallet as
USDC (the only asset the gate counts). Worst case per accepted call: gas only -
no principal is ever exposed (the flash loan is sourced and returned atomically),
bounded by gasLimit x clamped maxFeePerGas.

Paper mode simulates the executor call against the relay with the pinned runtime
override (state/executor-code.hex, eth_getCode of the fork deployment - no state
overrides needed, the flash loan funds itself); live mode sends through the signer
socket to the gate-deployed EXECUTOR_ADDR after verifying the deployed code (modulo
the owner immutable) and the owner. A confirmed successful receipt IS the payout
proof: the USDC profit transfer to the wallet happens inside the same transaction.
Every live send clamps maxFeePerGas so that gasLimit x maxFeePerGas x a fresh
ETH/USD read (UniV3 USDC/WETH spot) stays within the manifest's 15 USD bound.
"""
import json, os, time, re, urllib.request

WS = os.environ.get("BOT_WS", os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(WS, "logs", "bot.jsonl")
STATE_F = os.path.join(WS, "state", "cursor.json")
CODE_F = os.path.join(WS, "state", "executor-code.hex")
MODE = os.environ.get("BOT_MODE", "paper")
RELAY = os.environ["RPC_RELAY_URL"]
LANE = os.environ.get("RPC_LANE", "paper")

HUB = "0xDE12B620A8a714476A97EfD14E6F7180Ca653557"
ZCHF = "0xb58e61c3098d85632df34eecfb899a1ed80921cb"
TOPIC_STARTED = "0xc4b384b2c5ca32c8e77081f4083be594a1ea9ba34f208a9f9a458f70608585f5"
# paper-mode executor: the fork deployment of the proven proof run (manifest fork_evidence)
EXECUTOR_PAPER = "0x8f7a45ebde059392e46a46dcc14ab24681a961ea"
EXECUTOR = (os.environ.get("EXECUTOR_ADDR") or "").strip()
if re.fullmatch(r"0x[0-9a-fA-F]{40}", EXECUTOR or "x"):
    EXECUTOR = EXECUTOR.lower()
else:
    EXECUTOR = "" if MODE == "live" else EXECUTOR_PAPER  # live fails closed without the gate address
OWNER = "0x1111111111111111111111111111111111111111"  # paper-mode signer stand-in (the pinned fork deployment's deployer: owner = msg.sender is baked into the pinned runtime)
POLL_S = 60
MAX_OFFER = "20000000000000000000"  # 20 ZCHF cap per bid (tail tweak: skip big-offer short-phase challenges)
GAS_LIMIT = 1600000  # measured success gasUsed 1333585 (fork proof2, DutchFlashTail); worst case = GAS_LIMIT * fee
# funding route pools (verified by getters at head, run 70853f4f, 2026-11-15):
P_USDC_USDT = "0x3416cf6c708da44db2624d63ea0aaef7113527c6"  # UniV3 USDC/USDT 0.01, token0=USDC
P_ZCHF_USDT = "0x8e4318e2cb1ae291254b187001a59a1f8ac78cef"  # UniV3 ZCHF/USDT, token0=ZCHF
# collateral -> USDC exit pools, keyed by collateral token (factory getPool + token0/token1
# getters verified at head, run 70853f4f); a collateral token missing here is SKIPPED, never guessed.
TOKEN_EXIT = {
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",  # WETH/USDC 0.05
    "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0": "0x4622df6fb2d9bee0dcdacf545acdb6a2b2f4f863",  # wstETH/USDC 0.05
    "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf": "0x4548280ac92507c9092a511c7396cbea78fa9e49",  # BTC.b/USDC 0.3 (fork-proven)
}
MIN_PROFIT = str(5 * 10 ** 6)  # 5 USDC floor on the OWNER's USDC delta (guard inside the executor tx)
FEE_FLOOR, FEE_CAP = 10 ** 9, 20 * 10 ** 9  # maxFeePerGas clamp in wei; 200000 x 20 gwei = 0.004 ETH
USD_MAX = 15  # manifest max_loss_per_tx_usd: the fee cap is clamped by a fresh ETH/USD read
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
# fresh ETH/USD valuation venue: UniV3 USDC/WETH 0.05% mainnet pool (token0=USDC, token1=WETH
# measured by the farm morpho-watcher session; the mapping is re-verified on every read)
POOL_UNI = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"

import subprocess
def keccak(sig):
    return subprocess.run(["/opt/foundry/bin/cast", "keccak", sig], capture_output=True, text=True).stdout.strip()[:10]

def strip0x(h):
    return h[2:] if h[:2].lower() == "0x" else h  # the pinned file has no prefix, RPC results do

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

def eth_usd_price():
    """Fresh ETH/USD from the UniV3 USDC/WETH pool spot price (slot0 sqrtPriceX96).

    price_usd = 1e12 * 2^192 / sqrtP^2: the pool raw price is sqrtP^2 / 2^192 WETH wei
    per USDC raw unit (token0 USDC 6 dec, token1 WETH 18 dec -> 1 WETH = price_usd USD).
    Verifies the token mapping and fails closed (raises) on anything implausible."""
    t0 = "0x" + rpc("eth_call", [{"to": POOL_UNI, "data": keccak("token0()")}, "latest"])[-40:]
    t1 = "0x" + rpc("eth_call", [{"to": POOL_UNI, "data": keccak("token1()")}, "latest"])[-40:]
    if {t0.lower(), t1.lower()} != {USDC, WETH}:
        raise RuntimeError("pool %s token mapping changed: %s/%s" % (POOL_UNI, t0, t1))
    r = rpc("eth_call", [{"to": POOL_UNI, "data": keccak("slot0()")}, "latest"])
    sqrtP = int(r[2:66], 16)
    if sqrtP < 10 ** 30:
        raise RuntimeError("slot0 sqrtPriceX96 implausible: %d" % sqrtP)
    price = 10 ** 12 * 2 ** 192 // (sqrtP * sqrtP)  # USD per WETH
    if not 100 < price < 10 ** 6:
        raise RuntimeError("implausible ETH/USD %d from slot0" % price)
    return price

def usd_fee(gas_limit, base, price):
    """maxFeePerGas clamped by FEE_CAP and by USD_MAX / (gas_limit * ETH/USD); floor-bounded.
    Returns (fee_wei, bound_usd); the caller declines the send if bound_usd > USD_MAX."""
    fee_cap_usd = USD_MAX * 10 ** 18 // (gas_limit * price)
    fee = min(max(base * 2, FEE_FLOOR), min(FEE_CAP, max(fee_cap_usd, FEE_FLOOR)))
    return fee, gas_limit * fee * price / 10 ** 18

# --- cumulative live-loss stop (decisions/human/2026-11-09-promote-criteria.md §5) ---
# Realized loss = gas actually paid (gasUsed x effectiveGasPrice from the confirmed
# receipt, valued at the bot's fresh ETH/USD) plus any realized principal loss; the
# executor pays the gained collateral to the owner atomically and reverts otherwise,
# so a failed send costs gas only. At LIVE_LOSS_STOP_USD cumulative loss the bot
# stops sending and writes the reason to state/STOPPED.json.
LIVE_LOSS_STOP_USD = 30

def live_loss_settle(st, price):
    """Settle confirmed live sends' realized gas into st['live_loss']['usd'] (§5)."""
    if price is None:
        return  # no valuation: keep pending, settle on a later cycle
    keep = []
    for h in st["live_loss"]["pending"]:
        try:
            rcpt = rpc("eth_getTransactionReceipt", [h])
        except Exception:
            rcpt = None
        if rcpt is None:
            keep.append(h)
            continue
        gas_wei = int(rcpt.get("gasUsed") or "0x0", 16) * int(rcpt.get("effectiveGasPrice") or "0x0", 16)
        st["live_loss"]["usd"] += gas_wei * price / 10 ** 18  # wei x USD/wei = USD
    st["live_loss"]["pending"] = keep

def live_loss_stop_write(st):
    with open(os.path.join(WS, "state", "STOPPED.json"), "w") as f:
        json.dump({"reason": "cumulative live loss %.2f USD reached %d USD: stop sending" % (st["live_loss"]["usd"], LIVE_LOSS_STOP_USD),
                   "live_loss_usd": round(st["live_loss"]["usd"], 4), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, f)

def settle_ready(ch):
    """Confirm the sent bid: the executor paid the USDC profit to the bot wallet
    INSIDE the bid transaction (it reverts unless its USDC ends above the flash
    repayment + premium + minProfit, then transfers the surplus to the owner), so a
    confirmed successful receipt IS the payout proof - no separate payout transaction
    exists, and a reverted bid simply paid gas only. Returns the new
    status (review 2026-11-08T08:07Z fix: done only after a receipt with status 1)."""
    if not ch.get("tx"):
        log("settle_skipped", note="no tx hash recorded for the sent bid")
        return "skipped"
    try:
        rcpt = rpc("eth_getTransactionReceipt", [ch["tx"]])
    except Exception as e:
        log("settle_blocked", note="receipt read failed: %s" % str(e)[:120])
        return "sent"
    if rcpt is None:
        return "sent"  # still pending; retry next poll
    if int(rcpt.get("status") or "0x0", 16) != 1:
        log("settle_skipped", note="bid tx reverted: no payout, no collateral taken", tx=ch["tx"])
        return "skipped"
    log("settle", mode="live", tx=ch["tx"],
        note="bid confirmed: executor paid the USDC profit to the wallet inside the bid tx")
    return "done"

def main():
    # pinned constructor-patched executor runtime (the code proven on the fork); paper
    # injects it as an eth_call override, live uses it to verify the gate deployment.
    exec_code = open(CODE_F).read().strip() if os.path.exists(CODE_F) else ""
    head = int(rpc("eth_blockNumber", []), 16)
    # cursor persists across restarts (events while the bot was down are re-read); first start begins at head
    st = json.load(open(STATE_F)) if os.path.exists(STATE_F) else {"cursor": head, "challenges": {}}
    if not st.get("live_loss"):
        st["live_loss"] = {"usd": 0, "pending": []}  # cumulative live-loss stop (§5); absent in pre-2026-11-09 state files
    log("startup", mode=MODE, head=head, exec=EXECUTOR, code_sha=bool(exec_code),
        cursor=st["cursor"], reads="relay-only")

    next_wake = None  # chain seconds until a tracked challenge's Dutch price fully decays
    while True:
        try:
            head = int(rpc("eth_blockNumber", []), 16)
            blk = rpc("eth_getBlockByNumber", [hex(head), False])
            ts = int(blk["timestamp"], 16)
            if st["live_loss"]["pending"]:  # §5: settle confirmed live sends' realized gas (only when any are pending)
                try:
                    lp = eth_usd_price()
                except Exception:
                    lp = None
                live_loss_settle(st, lp)
            if MODE == "live" and st["live_loss"]["usd"] >= LIVE_LOSS_STOP_USD and not st["live_loss"].get("stop_logged"):
                # Fix (review 2026-11-09, attempt 677 parity): persist the §5 stop reason AS SOON AS
                # settlement reaches the threshold — the send-time check below only fires when another
                # eligible challenge appears, so without this the reason is never written while the
                # threshold sits crossed with no new challenges. Writes STOPPED.json exactly once
                # (the persisted stop_logged flag also guards the send-time branch below).
                st["live_loss"]["stop_logged"] = True
                live_loss_stop_write(st)
                log("send_stop", live_loss_usd=round(st["live_loss"]["usd"], 2), max_usd=LIVE_LOSS_STOP_USD,
                    reason="settlement reached the stop threshold without a new challenge: STOPPED.json persisted, sending stopped")
            base = int(blk.get("baseFeePerGas") or "0", 16)
            if st["cursor"] < head:
                logs = rpc("eth_getLogs", [{"address": [HUB], "topics": [TOPIC_STARTED],
                                            "fromBlock": hex(st["cursor"] + 1), "toBlock": hex(head)}])
                for lg in logs or []:
                    # ChallengeStarted(indexed challenger, indexed position, size, number):
                    # data = [size][number] -- word1 spans chars 66..130 of the 0x-prefixed hex string
                    num = int(lg["data"][66:130], 16)
                    pos = "0x" + lg["topics"][2][-40:]
                    st["challenges"][str(num)] = {"position": pos, "block": int(lg["blockNumber"], 16), "status": "open"}
                    log("event", num=num, position=pos, block=int(lg["blockNumber"], 16))
                st["cursor"] = head
            next_wake = None
            # act on tracked challenges
            for num, ch in list(st["challenges"].items()):
                if ch.get("status") in ("done", "skipped", "settled"):
                    continue  # attempt 1266 note 4: settled challenges must not be re-read every poll
                if ch.get("status") == "sent":
                    # the live bid is sent; a confirmed receipt retires the challenge -
                    # the payout happened inside the bid transaction itself (review fix)
                    ch["status"] = settle_ready(ch)
                    continue
                getter = keccak("challenges(uint256)") + "%064x" % int(num)
                r = rpc("eth_call", [{"to": HUB, "data": getter}, "latest"])
                # the hub's public array getter returns four UNPACKED words (measured on the fork
                # at reset 24776369: scratch/franken-decode-test.json): challenger, start, position, size
                vals = [r[i:i + 64] for i in (2, 66, 130, 194)]
                challenger = "0x" + vals[0][-40:]
                start = int(vals[1], 16)
                size = int(vals[3], 16)
                if challenger == "0x0000000000000000000000000000000000000000":
                    ch["status"] = "settled"
                    log("settled", num=num)
                    continue
                cd = rpc("eth_call", [{"to": ch["position"], "data": keccak("challengeData()")}, "latest"])
                phase = int(cd[66:130], 16)
                ch["start"], ch["phase"], ch["size"] = start, phase, size
                if ts < start + 2 * phase - 6:
                    ch["status"] = "waiting"
                    wake = start + 2 * phase - ts - 6  # bid at expiry-6: the Dutch price is a tiny known value there
                    next_wake = wake if next_wake is None else min(next_wake, wake)
                    continue
                # -6s reached: bid the full remaining size, paying at most MAX_OFFER ZCHF (offer decays to 0 at expiry)
                token = "0x" + rpc("eth_call", [{"to": ch["position"], "data": keccak("collateral()")}, "latest"])[-40:]
                ch["token"] = token  # persisted for the logs
                exit_pool = TOKEN_EXIT.get(token.lower())
                if exit_pool is None:
                    # fail closed: an unknown collateral token has no proven exit route
                    ch["status"] = "skipped"
                    log("skipped", num=num, token=token, note="collateral token has no verified UniV3 exit pool in TOKEN_EXIT")
                    continue
                data = keccak("bid(uint32,uint256,uint256,address,address,address,address,uint256)") + \
                    "%064x%064x%064x%064x%064x%064x%064x%064x" % (
                        int(num), size, int(MAX_OFFER), int(token, 16), int(exit_pool, 16),
                        int(P_USDC_USDT, 16), int(P_ZCHF_USDT, 16), int(MIN_PROFIT))
                ch["exit_pool"] = exit_pool  # persisted for the logs
                call_params = {"from": OWNER, "to": EXECUTOR, "data": data}
                if MODE == "paper":
                    if not exec_code:
                        ch["status"] = "waiting"  # fail closed: no pinned runtime, no simulation
                        continue
                    params = [call_params, "latest", {EXECUTOR: {"code": exec_code}}]  # no state overrides: the Aave flash loan funds the whole tx itself
                    try:
                        rpc("eth_call", params, lane="research")
                        sim = "ok"
                    except Exception as e:
                        sim = str(e)[:200]
                    log("simulate", num=num, size=size, sim=sim)
                    if sim != "ok":
                        # only a real executor revert is final; a transient relay error is retried next poll
                        ch["status"] = "skipped" if "revert" in sim.lower() else "waiting"
                        continue
                    log("sent", num=num, mode="paper",
                        note="simulated executor bid ok; size %d of token %s taken at offer <= maxOffer, flash-funded USDC->USDT->ZCHF, sold via exit %s; USDC profit (> %s raw units) paid to the owner inside the same tx (sim ok = payout ok)" % (size, token, exit_pool, MIN_PROFIT))
                    ch["status"] = "done"  # payout is atomic with the bid: nothing to sweep
                else:
                    # live: verify the gate deployment, then one signer send; a rejection is final
                    if st["live_loss"]["usd"] >= LIVE_LOSS_STOP_USD:  # §5 cumulative-loss stop: reason in state/STOPPED.json
                        if not st["live_loss"].get("stop_logged"):
                            st["live_loss"]["stop_logged"] = True
                            live_loss_stop_write(st)
                        log("send_stop", num=num, live_loss_usd=round(st["live_loss"]["usd"], 2), max_usd=LIVE_LOSS_STOP_USD)
                        continue
                    ok, note = live_ready(exec_code)
                    if not ok:
                        log("send_blocked", num=num, note=note)
                        continue  # leave the challenge open, retry next poll
                    try:
                        price = eth_usd_price()
                    except Exception as e:
                        log("send_blocked", num=num, note="price read failed: %s" % str(e)[:120])
                        continue  # fresh valuation unreadable: decline, retry next poll
                    fee, bound_usd = usd_fee(GAS_LIMIT, base, price)
                    if bound_usd > USD_MAX:
                        log("send_blocked", num=num,
                            note="signed gas bound %.2f USD > $%d at ETH/USD %d" % (bound_usd, USD_MAX, price))
                        continue
                    resp = signer({"op": "send", "chain": "ethereum", "to": EXECUTOR, "data": data,
                                   "gas": hex(GAS_LIMIT), "value": "0x0",
                                   "maxFeePerGas": hex(fee), "maxPriorityFeePerGas": hex(fee // 10)})
                    log("sent", num=num, mode="live", ok=bool(resp.get("ok")),
                        txHash=resp.get("txHash"), err=(resp.get("error") or "")[:160],
                        bound_eth=round(GAS_LIMIT * fee / 10 ** 18, 6), bound_usd=round(bound_usd, 2),
                        price_usd=price, fee_wei=fee)
                    if resp.get("ok") is True:
                        ch["status"], ch["tx"] = "sent", resp.get("txHash")
                        if resp.get("txHash"):
                            st["live_loss"]["pending"].append(resp["txHash"])  # settle its realized gas once the receipt is visible
                    else:
                        ch["status"] = "skipped"
            log("heartbeat", head=head, cursor=st["cursor"], live_loss_usd=round(st["live_loss"]["usd"], 4), live_loss_stop_usd=LIVE_LOSS_STOP_USD,
                pending={k: v.get("status") for k, v in st["challenges"].items() if v.get("status") not in ("settled", "done")})
            json.dump(st, open(STATE_F, "w"))
        except Exception as e:
            log("error", error=str(e)[:300])
        time.sleep(min(POLL_S, max(3, next_wake)) if next_wake else POLL_S)

def live_ready(exec_code):
    """Verify the gate-deployed executor (code, owner) before any live send; fail closed.

    The proven runtime pin was built with the paper owner (constructor-patched immutable),
    so the deployed runtime of the gate-owned deployment differs exactly by its owner
    address. Read the deployed owner first, then compare the deployed runtime with the
    proven one after neutralizing each side's owner-address occurrences (review fix)."""
    try:
        owner_ret = "0x" + rpc("eth_call", [{"to": EXECUTOR, "data": keccak("owner()")}, "latest"])[-40:]
        me = signer({"op": "address"})
        me_addr = (me.get("address") or me.get("addr") or "") if isinstance(me, dict) else ""
    except Exception as e:
        return False, "owner/address read failed: %s" % str(e)[:120]
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", me_addr or "x"):
        return False, "signer address unreadable"
    if owner_ret.lower() != me_addr.lower():
        return False, "executor owner %s != our wallet %s" % (owner_ret, me_addr)
    try:
        code = rpc("eth_getCode", [EXECUTOR, "latest"])
    except Exception as e:
        return False, "eth_getCode failed: %s" % str(e)[:120]
    if not code or code == "0x":
        return False, "executor %s has no deployed code" % EXECUTOR
    if len(strip0x(code)) != len(strip0x(exec_code)):
        return False, "deployed runtime length differs from the pinned proven runtime"
    na = strip0x(code).lower().replace(me_addr[2:].lower(), "0" * 40)
    nb = strip0x(exec_code).lower().replace(OWNER[2:], "0" * 40)
    if na != nb:
        return False, "deployed runtime differs from the proven artifact beyond the owner"
    return True, "ok"

if __name__ == "__main__":
    main()
