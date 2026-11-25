#!/usr/bin/env python3
# swell-fee-auction-ethereum: buys the Swell fee auction (Fee Flow fork 0xf17b5814) in one transaction when a
# large fee mint makes its pot worth more than its SWELL price (lead 359, wiki mechanisms/swell-fee-auction.md).
# Trigger: a confirmed Transfer(from 0x0) of swETH / rswETH to the auction, delivered by farm-feed; safety poll
# every 300 s. Decision: eth_call of the executor's run() (returns the profit in wrapped native); send only when
# that profit clears minProfit = signed gas cap + margin, which the executor enforces again on-chain.
# Paper: eth_call with the fork-proven runtime as a code override, sends nothing. Live: signer, private route.
import json, os, sys, time, urllib.request, urllib.error

RELAY = os.environ.get("RPC_RELAY_URL", "http://127.0.0.1:8545").rstrip("/")
LANE = os.environ.get("RPC_LANE", "paper")
MODE = os.environ.get("BOT_MODE", "paper")
FEED = os.environ.get("FEED_URL", "http://127.0.0.1:8546").rstrip("/")
CHAIN = "ethereum"
EXEC = os.environ.get("EXECUTOR_ADDR", "")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append("/opt/farm/lib")

SIM_FROM = "0x1111111111111111111111111111111111111111"   # owner baked into the fork-deployed runtime
SIM_EXEC = "0x8f7a45ebde059392e46a46dcc14ab24681a961ea"   # paper only: address the runtime override is placed at
RUNTIME = open(os.path.join(HERE, "executor-runtime.hex")).read().strip()
TPL = json.load(open(os.path.join(HERE, "templates.json")))

MORPHO = "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb"
WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
AUCTION = "0xf17b581496bc2669ce0931facaa1ade35029e85d"
RSWETH = "0xfae103dc9cf190ed75350761e95403b7b8afa6c0"
SWETH = "0xf951e335afb289353dc249e82926178eac7ded78"
WEETH = "0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee"
ROUTER = "0x66a9893cc07d91d95644aedd05d03f95e1dba8af"
PERMIT2 = "0x000000000022d473030f116ddee9f6b43ac78ba3"
CURVE1 = "0x278cfb6f06b1efc09d34fc7127d6060c61d629db"   # rswETH -> weETH, exchange(1, 0)
CURVE2 = "0xdb74dfdd3bb46be8ce6c33dc9d82777bcfc3ded5"   # weETH -> WETH, exchange(1, 0)
T_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO32 = "0x" + "0" * 64

ROUTER02 = "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45"   # Uniswap V3 SwapRouter02 (factory() / WETH9() checked)
V3_FEE = 500                                              # swETH / WETH pool 0x30ea22c8... fee()
RUN_SEL = "4b6b9320"           # run((...)) selector, from cast calldata (mk_bot_files.py compares the whole encoding)
FLASH = 10 * 10**18            # WETH flashed; only what the SWELL costs is spent, the rest is swept back
GAS_LIMIT = 1_200_000          # fork success used 784,138
MAX_FEE = 5 * 10**9            # signed maxFeePerGas
MAX_PRIO = 2 * 10**9
GAS_CAP_WEI = GAS_LIMIT * MAX_FEE              # 0.006 ETH: worst-case loss of one transaction
MIN_PROFIT = GAS_CAP_WEI + 2 * 10**15          # executor reverts below this, so an included tx nets > 0 after gas
DEADLINE_BLOCKS = 3
SAFETY_S = 300
FEED_TIMEOUT = 55
MAXU = 2**256 - 1


class CuCap(Exception):
    pass


def log(obj):
    obj = dict(obj, ts=int(time.time()))
    line = json.dumps(obj)
    print(line, flush=True)
    with open(os.path.join("logs", "bot.jsonl"), "a") as f:
        f.write(line + "\n")


def rpc(method, params, timeout=60):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"{RELAY}/{CHAIN}?lane={LANE}", body, {"Content-Type": "application/json"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        txt = e.read().decode("utf8", "replace")[:300]
        if e.code == 429 or "cap" in txt.lower() or "budget" in txt.lower() or "quota" in txt.lower():
            raise CuCap(txt)
        raise RuntimeError(f"http {e.code} {txt}")
    if "error" in r:
        txt = json.dumps(r["error"])[:400]
        if "daily" in txt.lower() and ("cap" in txt.lower() or "budget" in txt.lower() or "quota" in txt.lower()):
            raise CuCap(txt)
        raise RuntimeError(txt)
    return r["result"]


def w(v):
    return f"{v:064x}"


def a32(a):
    return a[2:].lower().rjust(64, "0")


def set_word(cd, idx, word):
    p = 10 + 64 * idx
    return cd[:p] + word + cd[p + 64:]


def enc_bytes(hexdata):
    b = hexdata[2:] if hexdata.startswith("0x") else hexdata
    n = len(b) // 2
    return w(n) + b + "0" * ((64 - len(b) % 64) % 64)


def enc_router_call(data, words):
    by = enc_bytes(data)
    return w(0x40) + w(0x40 + len(by) // 2) + by + w(len(words)) + "".join(w(x) for x in words)


def run_calldata(executor, epoch, min_profit, deadline_block, v3=False):
    """ABI encoding of run(Params) for FeeAuctionBuy; see contracts/src/FeeAuctionBuy.sol for the struct.
    v3=False: swETH is sold through the Universal Router (v4 pool). v3=True: through the Uniswap V3 0.05 % pool
    (SwapRouter02), which is the route that works when the v4 pool cannot take the size."""
    far = w(2**63)
    buy = set_word(TPL["buy"], 2, far)                 # router deadline
    buy = set_word(buy, 26, w(FLASH))                  # amountInMaximum (native)
    buy = set_word(buy, 31, w(FLASH))                  # SETTLE_ALL max
    buy = set_word(buy, 37, a32(executor))             # SWEEP recipient of unused native
    sell = set_word(TPL["sell"], 2, far)
    assets = w(2) + a32(RSWETH) + a32(SWETH)
    buy_e = enc_router_call(buy, [25, 34])             # words the executor overwrites with getPrice()
    sell_e = enc_router_call(sell, [24, 30])           # words the executor overwrites with its swETH balance
    legs = w(2) + a32(CURVE1) + a32(RSWETH) + w(1) + w(0) + a32(CURVE2) + a32(WEETH) + w(1) + w(0)
    v3legs = (w(1) + a32(ROUTER02) + a32(SWETH) + a32(WETH) + w(V3_FEE)) if v3 else w(0)
    sell_token = ("0x" + "0" * 40) if v3 else SWETH     # address(0): the executor skips the router sell
    head_n = 16 * 32
    o_assets = head_n
    o_buy = o_assets + len(assets) // 2
    o_sell = o_buy + len(buy_e) // 2
    o_legs = o_sell + len(sell_e) // 2
    o_v3 = o_legs + len(legs) // 2
    head = (a32(MORPHO) + a32(WETH) + w(FLASH) + a32(AUCTION) + w(o_assets) + w(epoch) + w(MAXU) + a32(ROUTER) + a32(PERMIT2)
            + w(o_buy) + a32(sell_token) + w(o_sell) + w(o_legs) + w(o_v3) + w(min_profit) + w(deadline_block))
    return "0x" + RUN_SEL + w(0x20) + head + assets + buy_e + sell_e + legs + v3legs


def call_u(to, sel_hex, arg=""):
    return int(rpc("eth_call", [{"to": to, "data": "0x" + sel_hex + arg}, "latest"]), 16)


def read_state():
    price = call_u(AUCTION, "98d5fdca")                                  # getPrice()
    slot0 = rpc("eth_call", [{"to": AUCTION, "data": "0xc9ae5e0c"}, "latest"])[2:]   # getSlot0() -> (locked, epochId, initPrice, startTime)
    epoch = int(slot0[64:128], 16)
    sw = call_u(SWETH, "70a08231", a32(AUCTION))
    rsw = call_u(RSWETH, "70a08231", a32(AUCTION))
    return {"price": price, "epoch": epoch, "sweth": sw, "rsweth": rsw, "start": int(slot0[192:256], 16)}


def wallet_address():
    if MODE != "live":
        return SIM_FROM
    import farmbot_signer
    a = farmbot_signer.my_address()
    return a["address"] if isinstance(a, dict) else a


def wait_receipt(txh, deadline_block):
    """Private send: no receipt once the deadline block has passed means it was never included (cost nothing)."""
    while True:
        rc = rpc("eth_getTransactionReceipt", [txh])
        if rc:
            log({"ev": "send_result", "tx": txh, "status": int(rc["status"], 16), "block": int(rc["blockNumber"], 16),
                 "gas_used": int(rc["gasUsed"], 16), "won": int(rc["status"], 16) == 1})
            return
        if int(rpc("eth_blockNumber", []), 16) > deadline_block + 1:
            log({"ev": "private_not_included", "tx": txh, "deadline_block": deadline_block})
            return
        time.sleep(4)


def evaluate(st, from_addr, why):
    to = EXEC if MODE == "live" else SIM_EXEC
    head = int(rpc("eth_blockNumber", []), 16)
    deadline = head + DEADLINE_BLOCKS
    row = {"ev": "opportunity_check", "why": why, "head": head, "epoch": st["epoch"], "price_swell": st["price"] / 1e18,
           "pot_sweth": st["sweth"] / 1e18, "pot_rsweth": st["rsweth"] / 1e18, "min_profit_eth": MIN_PROFIT / 1e18}
    t0 = time.time()
    best, errs = None, {}
    for route, v3 in (("v4", False), ("v3", True)):        # both swETH routes are simulated; the better one is sent
        d = run_calldata(to, st["epoch"], MIN_PROFIT, deadline, v3)
        tx = {"from": from_addr, "to": to, "data": d, "gas": hex(GAS_LIMIT)}
        try:
            res = rpc("eth_call", [tx, "latest"] + ([] if MODE == "live" else [{to: {"code": RUNTIME}}]))
            pr = int((res or "0x0")[2:] or "0", 16)
            if best is None or pr > best[0]:
                best = (pr, route, d)
        except CuCap:
            raise
        except Exception as e:
            errs[route] = str(e)[:160]
        if not st["sweth"]:
            break                                           # no swETH in the pot: the two routes are the same
    if best is None:
        log(dict(row, result="revert", err=errs, ms=int((time.time() - t0) * 1000)))
        return False
    profit, route, data = best
    row.update(result="profitable", route=route, profit_eth=profit / 1e18, gas_cap_eth=GAS_CAP_WEI / 1e18,
               other_route_err=errs, ms=int((time.time() - t0) * 1000))
    log(row)
    base = int(rpc("eth_getBlockByNumber", ["latest", False])["baseFeePerGas"], 16)
    if base + MAX_PRIO > MAX_FEE:
        log({"ev": "skip_fee_gate", "base_gwei": round(base / 1e9, 3), "profit_eth": profit / 1e18})
        return False
    if MODE != "live":
        log({"ev": "paper_sim", "would_send": True, "profit_eth": profit / 1e18, "deadline_block": deadline,
             "net_after_gas_cap_eth": (profit - GAS_CAP_WEI) / 1e18})
        return True
    try:
        import farmbot_signer
        r = farmbot_signer.send(CHAIN, EXEC, data, 0, GAS_LIMIT, MAX_FEE, MAX_PRIO)
        log({"ev": "send", "reply": json.dumps(r, default=str)[:300], "profit_eth": profit / 1e18, "deadline_block": deadline})
        txh = r.get("tx_hash") or r.get("hash") if isinstance(r, dict) else None
        if txh:
            wait_receipt(txh, deadline)
    except CuCap:
        raise
    except Exception as e:
        log({"ev": "signer_err", "err": str(e)[:200]})   # a signer rejection is final: no retry of this opportunity
    return True


def feed_wait(cursor, until):
    """Long-poll farm-feed for mints of swETH / rswETH. Returns (cursor, reason) where reason is None (keep waiting,
    nothing for us), 'mint_to_auction', or 'reread' (gap / 429 / 503 / error: state must be re-read)."""
    q = (f"{FEED}/logs/{CHAIN}?address={SWETH},{RSWETH}&topic0={T_TRANSFER}&topic1={ZERO32}"
         f"&timeout={max(5, min(FEED_TIMEOUT, int(until - time.time())))}")
    if cursor:
        q += f"&after={cursor}"
    try:
        r = json.loads(urllib.request.urlopen(q, timeout=FEED_TIMEOUT + 15).read())
    except Exception as e:
        # 429 (filter slots full / feed budget), 503 or a connection error: fall back to the safety interval,
        # then re-read state through the relay (never a tight loop: 4 reads per SAFETY_S at most)
        log({"ev": "feed_err", "err": str(e)[:150], "fallback_sleep_s": int(max(5, until - time.time()))})
        time.sleep(max(5, until - time.time()))
        return cursor, "reread"
    cursor = r.get("cursor", cursor)
    if r.get("gap"):
        log({"ev": "feed_gap"})
        return cursor, "reread"
    for l in r.get("logs", []):
        if l.get("removed"):
            return cursor, "reread"
        if len(l.get("topics", [])) == 3 and l["topics"][2][-40:] == AUCTION[2:]:
            log({"ev": "mint_to_auction", "token": l["address"], "amount": int(l["data"], 16) / 1e18,
                 "block": int(l["blockNumber"], 16), "tx": l["transactionHash"], "block_ts": l.get("blockTimestamp")})
            return cursor, "mint_to_auction"
    return cursor, None


def sleep_to_midnight():
    now = time.time()
    time.sleep(max(60, 86400 - now % 86400 + 30))


def main():
    os.makedirs("logs", exist_ok=True)
    os.makedirs("state", exist_ok=True)
    if MODE == "live" and not EXEC:
        log({"ev": "fatal", "msg": "EXECUTOR_ADDR unset"})
        sys.exit(1)
    from_addr = None
    cursor = None
    why = "start"
    last_done = None            # (epoch, sweth, rsweth) of the last opportunity acted on: act once per state
    while True:
        try:
            if from_addr is None:
                from_addr = wallet_address()
                log({"ev": "start", "mode": MODE, "from": from_addr, "executor": EXEC or ("paper-override:" + SIM_EXEC),
                     "min_profit_eth": MIN_PROFIT / 1e18, "gas_cap_eth": GAS_CAP_WEI / 1e18})
            st = read_state()
            key = (st["epoch"], st["sweth"], st["rsweth"])
            log({"ev": "state", "why": why, "epoch": st["epoch"], "price_swell": st["price"] / 1e18,
                 "pot_sweth": st["sweth"] / 1e18, "pot_rsweth": st["rsweth"] / 1e18, "epoch_start": st["start"]})
            if (st["sweth"] or st["rsweth"]) and key != last_done:
                if evaluate(st, from_addr, why):
                    last_done = key
            until = time.time() + SAFETY_S
            why = "safety_poll"
            while time.time() < until:
                cursor, reason = feed_wait(cursor, until)
                if reason:
                    why = reason
                    break
        except CuCap as e:
            log({"ev": "cu_cap", "err": str(e)[:150]})
            sleep_to_midnight()
        except Exception as e:
            log({"ev": "loop_err", "err": str(e)[:200]})
            time.sleep(30)


if __name__ == "__main__":
    main()
