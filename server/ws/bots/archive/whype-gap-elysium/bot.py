#!/usr/bin/env python3
"""whype-gap-elysium: holding-frame mean reversion of Elysium pool A (USDC/WHYPE) vs HyperCore spot.

The pool 0x97796d80b6a1db78632f7451196b04f307329eb6 (UniV3-style, token0=USDC 6dp,
token1=WHYPE 18dp) prices WHYPE at a persistent ~-0.86% median discount to the
HyperCore reference (Hyperliquid HYPE 1m closes); gaps of <= -1% open ~10 times a
day and last minutes (attempt 1276, 26.5 h sample). The bot buys WHYPE with USDC in
that pool when the gap crosses -1%, holds in the executor, and sells back in the SAME
pool when the gap closes past -0.1% (take), when the reference falls 5% under the
entry reference (stop), or at 24 h (frame timeout). Profit is realized in the pool in
USDC; the reference is only a signal (the -0.86% baseline is why the entry line is
-1%, not 0). Detection timing: pool slot0 every 10 s (>= R = 3 s race rule), the
reference updates at 1-minute granularity exactly as in the measurement.

Paper mode: state machine + executor-quote simulation through the relay with the
pinned fork runtime (state/executor-code.hex at bots/paper/<id>/state/); every
decision is logged. Live mode: sends buy/sell to the gate-deployed EXECUTOR_ADDR
through the signer.
"""
import json, os, re, statistics, subprocess, time, urllib.request

WS = os.environ.get("BOT_WS", os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(WS, "logs", "bot.jsonl")
STATE_F = os.path.join(WS, "state", "state.json")
CODE_F = os.path.join(WS, "state", "executor-code.hex")
MODE = os.environ.get("BOT_MODE", "paper")
RELAY = os.environ["RPC_RELAY_URL"]
LANE = os.environ.get("RPC_LANE", "paper")
CHAIN = "elysium"

POOL = "0x97796d80b6a1db78632f7451196b04f307329eb6"
USDC = "0xb47c4c8f73f009cc0c0d3f92b388d13e293f0b65"
WHYPE = "0xba876237b0f021a6c6d852d6c26e107997cc5e81"
HL_INFO = os.environ.get("HYPERLIQUID_URL", "https://api.hyperliquid.xyz/info")

ENTRY_GAP = -0.010    # buy when pool/ref - 1 <= -1.0% (measured line, attempt 1276)
EXIT_GAP = -0.001     # sell (take) when the gap closes past -0.1%
STOP_REF = 0.95       # sell (stop) when ref <= entry_ref * 0.95 (-5%, frame worst case)
HOLDING_MAX_S = 24 * 3600
SIZE_USDC = 20 * 10**6          # holding_usd 20, whole capital, one position
SLIP = 995                      # min-out guards at 99.5% of quote

# paper-mode executor: fork deployment of the proof run (manifest fork_evidence)
EXECUTOR_PAPER = os.environ.get("FORK_EXECUTOR_PAPER", "0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352")
EXECUTOR = (os.environ.get("EXECUTOR_ADDR") or "").strip()
if re.fullmatch(r"0x[0-9a-fA-F]{40}", EXECUTOR or "x"):
    EXECUTOR = EXECUTOR.lower()
else:
    EXECUTOR = "" if MODE == "live" else EXECUTOR_PAPER.lower()

POLL_S = 10
HEARTBEAT_EVERY = 6            # 60 s baseline heartbeat
GAP_WINDOW = 360               # rolling gap samples (~1 h) for baseline calibration logs

def sel(fn):
    return subprocess.run(["/opt/foundry/bin/cast", "sig", fn], capture_output=True, text=True).stdout.strip()

def calldata(fn, args=None):
    cmd = ["/opt/foundry/bin/cast", "calldata", fn] + (args or [])
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()

def rpc(method, params, timeout=40, overrides=None):
    p = list(params)
    if overrides is not None:
        p.append(overrides)
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": p}).encode()
    req = urllib.request.Request("%s/%s?lane=%s" % (RELAY, CHAIN, LANE), data=body,
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
        s.settimeout(120)
        s.connect(os.environ["SIGNER_SOCK"])
        s.sendall((json.dumps(req) + "\n").encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    return json.loads(buf or b'{"ok": false, "error": "no response"}')

def hl_reference(now):
    """HyperCore reference = latest CLOSED Hyperliquid HYPE 1m candle close (as measured)."""
    body = json.dumps({"type": "candleSnapshot",
                       "req": {"coin": "HYPE", "interval": "1m",
                               "startTime": int((now - 12 * 60) * 1000), "endTime": int(now * 1000)}}).encode()
    req = urllib.request.Request(HL_INFO, data=body, headers={"content-type": "application/json"})
    candles = json.loads(urllib.request.urlopen(req, timeout=20).read())
    closed = [c for c in candles if int(c["T"]) <= now * 1000]
    if not closed:
        raise RuntimeError("no closed 1m candle")
    return float(closed[-1]["c"])

def pool_price():
    r = rpc("eth_call", [{"to": POOL, "data": sel("slot0()")}, "latest"])
    sqrtP = int(r[2:66], 16)
    tick = int.from_bytes(bytes.fromhex(r[66:130]), "big", signed=True)
    if not (10**32 < sqrtP < 10**36):  # measured sqrtP ~9.86e33 at ~64 USDC/WHYPE; the price check below is the real guard
        raise RuntimeError("slot0 sqrtPriceX96 implausible: %d" % sqrtP)
    price = 1e12 * (2**96 / sqrtP) ** 2  # USDC per WHYPE
    if not (1.0 < price < 1e4):
        raise RuntimeError("implausible USDC/WHYPE price %f" % price)
    return price, tick

def executor_quote_exit(whype_amt):
    """Call the executor's own quoteExit(pool, amt) on mainnet state via the pinned
    runtime override - the exact guard math the live executor will apply."""
    code = open(CODE_F).read().strip()
    data = calldata("quoteExit(address,uint256)", [POOL, str(whype_amt)])
    ov = {EXECUTOR: {"code": "0x" + code}}
    r = rpc("eth_call", [{"to": EXECUTOR, "data": data}, "latest"], overrides=ov)
    return int(r, 16)

def token_balance(token, who):
    r = rpc("eth_call", [{"to": token, "data": calldata("balanceOf(address)", [who])}, "latest"])
    return int(r, 16)

def load_state():
    try:
        with open(STATE_F) as f:
            return json.load(f)
    except Exception:
        return {"holding": False, "entry_t": 0, "entry_ref": 0.0, "entry_cost": 0,
                "whype": 0, "gaps": [], "round_trips": [], "sends": []}

def save_state(st):
    tmp = STATE_F + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f)
    os.replace(tmp, STATE_F)

_botw = None

def bot_wallet():
    """Address the executor's onlyBot modifier accepts (its immutable bot())."""
    global _botw
    if _botw is None and EXECUTOR:
        r = rpc("eth_call", [{"to": EXECUTOR, "data": sel("bot()")}, "latest"])
        _botw = ("0x" + r[-40:]).lower()
    return _botw

def gas_limit_for(frm, to, data):
    # Nitro rule: every gas limit comes from eth_estimateGas, never a constant.
    # Extra floor: the pool swap hook reverts "IG" unless gasleft() >= 250,000 at
    # its afterSwap check (slot 2 hi32; fork proof 2026-11-15: sell failed with
    # gasLimit 0x8aee4 (569k, 302,955 used -> ~258k left at hook), succeeded with
    # a 3,000,000 limit), so add a full 1M floor on top of the estimate.
    est = int(rpc("eth_estimateGas", [{"from": frm, "to": to, "data": data}]), 16)
    return max(est * 13 // 10, est + 1000000)

def live_send(fn_sig, args):
    data = calldata(fn_sig, args)
    gas_limit = gas_limit_for(bot_wallet() or EXECUTOR, EXECUTOR, data)
    res = signer({"op": "send", "chain": CHAIN, "to": EXECUTOR, "data": data,
                  "gas_limit": gas_limit})
    log("send", mode=MODE, sig=fn_sig, args=args, ok=bool(res.get("ok")),
        tx=res.get("tx_hash") or res.get("hash") or "", raw=str(res)[:300])
    return res

def wait_receipt(h, tries=40):
    for _ in range(tries):
        try:
            r = rpc("eth_getTransactionReceipt", [h])
        except Exception:
            r = None
        if r is not None:
            return r
        time.sleep(3)
    return None

def main():
    if MODE == "live" and not EXECUTOR:
        log("fatal", reason="EXECUTOR_ADDR unset in live mode")
        raise SystemExit(1)
    if MODE == "live":
        log("live_ready", executor=EXECUTOR)
    st = load_state()
    ref, ref_t = None, 0.0
    n = 0
    log("start", mode=MODE, pool=POOL, entry_gap=ENTRY_GAP, exit_gap=EXIT_GAP,
        stop_ref=STOP_REF, holding_max_s=HOLDING_MAX_S, size_usdc=SIZE_USDC,
        executor=EXECUTOR)
    while True:
        t0 = time.time()
        n += 1
        try:
            now = time.time()
            if now - ref_t >= 55 or ref is None:
                try:
                    ref = hl_reference(now)
                    ref_t = now
                except Exception as e:
                    log("reference_error", err=str(e)[:200])
            price, tick = pool_price()
        except Exception as e:
            log("poll_error", err=str(e)[:200])
            time.sleep(30)
            continue
        gap = price / ref - 1.0 if ref else 0.0
        st["gaps"] = (st.get("gaps") + [gap])[-GAP_WINDOW:]
        base = statistics.median(st["gaps"]) if len(st["gaps"]) >= 10 else None
        act = None
        if ref is None:
            act = "no_reference"
        elif not st["holding"]:
            if gap <= ENTRY_GAP:
                act = "buy"
        else:
            if gap >= EXIT_GAP:
                act = "sell_take"
            elif ref <= st["entry_ref"] * STOP_REF:
                act = "sell_stop"
            elif now - st["entry_t"] >= HOLDING_MAX_S:
                act = "sell_timeout"

        if act == "buy":
            # SIZE_USDC is raw 6dp USDC; whype raw = usdc_raw / price * 1e12 (18dp/6dp)
            exp_whype = int(SIZE_USDC * 10**12 // price)
            est_whype = exp_whype * SLIP // 1000  # conservative floor
            q = None
            try:
                # quote for the expected received WHYPE: executor guard math on live state
                q = executor_quote_exit(exp_whype)
            except Exception as e:
                log("quote_error", err=str(e)[:200])
            if MODE == "paper":
                st.update(holding=True, entry_t=now, entry_ref=ref, entry_cost=SIZE_USDC,
                          whype_est=int(SIZE_USDC * 10**12 // price))  # 6dp USDC / price -> 18dp WHYPE (x1e12, not x1e18)
                log("sim_buy", price=price, ref=ref, gap=round(gap, 6), est_whype=str(est_whype),
                    exec_quote_exit_usdc=q, baseline=round(base, 6) if base else None)
            else:
                u0 = token_balance(USDC, EXECUTOR)
                if u0 < SIZE_USDC:
                    td = calldata("transfer(address,uint256)", [EXECUTOR, str(SIZE_USDC)])
                    r = signer({"op": "send", "chain": CHAIN, "to": USDC,
                                "data": td,
                                "gas_limit": gas_limit_for(bot_wallet() or "", USDC, td)})
                    log("fund_executor", ok=bool(r.get("ok")), raw=str(r)[:200])
                # Guard note: minExitUsdc is enforced ON-CHAIN inside buy() against
                # quoteExit(pool, got) - the post-buy executable quote of the full
                # received amount at the post-trade price (WhypeGap.sol:80-82), not
                # a pre-trade spot check.
                min_exit = SIZE_USDC * SLIP // 1000
                r = live_send("buy(address,uint256,uint256,uint256)",
                              [POOL, str(SIZE_USDC), str(est_whype), str(min_exit)])
                h = r.get("tx_hash") or r.get("hash")
                rcpt = wait_receipt(h) if h else None
                ok = bool(rcpt) and rcpt.get("status") == "0x1"
                if ok:
                    w1 = token_balance(WHYPE, EXECUTOR)
                    st.update(holding=True, entry_t=now, entry_ref=ref, entry_cost=SIZE_USDC, whype=w1)
                log("buy_sent", ok=ok, usdc_before=u0, gas=rcpt.get("gasUsed") if rcpt else None)
            save_state(st)
        elif act in ("sell_take", "sell_stop", "sell_timeout"):
            held = st.get("whype") or st.get("whype_est") or 0
            q = None
            try:
                q = executor_quote_exit(held) if held else None
            except Exception as e:
                log("quote_error", err=str(e)[:200])
            pnl = (q - st["entry_cost"]) / 1e6 if q else None
            if MODE == "paper":
                st["round_trips"] = (st.get("round_trips") + [
                    {"t_in": st["entry_t"], "t_out": now, "why": act,
                     "pnl_usdc_est": pnl, "gap_in": None, "gap_out": round(gap, 6)}])[-500:]
                log("sim_" + act, price=price, ref=ref, gap=round(gap, 6),
                    held_whype=str(held), exec_quote_exit_usdc=q, pnl_usdc_est=pnl,
                    hold_s=int(now - st["entry_t"]))
                st.update(holding=False, whype=0, whype_est=0)
            else:
                min_out = q * SLIP // 1000 if q else 0
                u0 = token_balance(USDC, EXECUTOR)
                r = live_send("sell(address,uint256)", [POOL, str(min_out)])
                h = r.get("tx_hash") or r.get("hash")
                rcpt = wait_receipt(h) if h else None
                ok = bool(rcpt) and rcpt.get("status") == "0x1"
                if ok:
                    u1 = token_balance(USDC, EXECUTOR)
                    st["round_trips"] = (st.get("round_trips") + [
                        {"t_in": st["entry_t"], "t_out": now, "why": act,
                         "usdc_in": st["entry_cost"], "usdc_out": u1 - u0,
                         "pnl_usdc": (u1 - u0 - st["entry_cost"]) / 1e6}])[-500:]
                    st.update(holding=False, whype=0)
                log("sell_sent", why=act, ok=ok, quote=q)
            save_state(st)
        elif n % HEARTBEAT_EVERY == 0:
            log("heartbeat", price=round(price, 4), ref=round(ref, 4) if ref else None,
                gap=round(gap, 6), holding=st["holding"],
                baseline=round(base, 6) if base is not None else None,
                gaps_n=len(st["gaps"]), ref_age_s=round(now - ref_t))
        save_state(st)
        time.sleep(max(1.0, POLL_S - (time.time() - t0)))

if __name__ == "__main__":
    main()
