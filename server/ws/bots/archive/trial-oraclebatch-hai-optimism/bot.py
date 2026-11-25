#!/usr/bin/env python3
# trial-oraclebatch-hai-optimism  (TRIAL bot, lead 213, decision 2026-11-17-cheap-chain-trials)
#
# HAI OracleJob on optimism pays 0.05 HAI to anyone calling workUpdateCollateralPrice(cType)
# once per collateral item per hour. Several items share one due second (OP, RETH, TBTC,
# VELO, WETH; HAIAERO + MSETH): the incumbents take such a cluster in ONE transaction.
# This bot does the same: for every window with >= MIN_CLUSTER items due together it sends
# ONE executor call for the whole cluster, timed to land in the first block whose timestamp
# is >= due. The executor does the jobs -> CoinJoin.exit -> HAI/WETH UniV3 sell -> unwrap ->
# ETH to the wallet and reverts unless ETH out >= minProfit (= signed gas cap + L1 estimate
# + 1). A view probe on the first item's oracle ends a lost race at ~36k gas. The sale pool
# is a call argument (POOL below); the executor has no baked pool.
# Single-item windows are left to the sibling trial-oraclejob-hai-optimism.
#
# The incumbents' usual bid on the 5-item window (0.19 gwei x 660k gas, 74% of the gross)
# cannot be matched under the rule "expected gross > signed gas cap" (our path needs a
# 950k limit because it also sells the HAI). The bot therefore bids a fixed 0.10 gwei and
# wins only the windows where the top bidders are absent or bid low (2 of 12 in the 12 h
# before placement). Win or lose, every window logs the taker, its block and its bid.
#
# paper: sends nothing; simulates the executor (code override of the fork deployment,
#        block time overridden to `due`) and records the taker of every window.
# live : one signer send per window, only if expected gross > signed gas cap + L1 est.
import json, os, sys, time, urllib.request

RELAY = os.environ.get("RPC_RELAY_URL", "http://127.0.0.1:8545")
LANE = os.environ.get("RPC_LANE", "paper")
MODE = os.environ.get("BOT_MODE", "paper")
EXEC = os.environ.get("EXECUTOR_ADDR", "")
CHAIN = "optimism"
HERE = os.path.dirname(os.path.abspath(__file__))

JOB = "0xF4F18205D8D46638489865e42c0a71a3d4F9FC22"       # HAI OracleJob
RELAYER = "0x6270403b908505f02da05be5c1956abb59fdb3a6"   # JOB.oracleRelayer()
POOL = "0x146b020399769339509c98B7B353d19130C150EC"      # UniV3 HAI/WETH fee 3000, token0 = HAI; passed to act() per call

# selectors: all from `cast sig`
SEL_ACT = "0x3b796add"          # act(bytes32[],address,address,uint256,uint256)
SEL_CPARAMS = "0xe54201f6"      # cParams(bytes32) at the OracleRelayer -> word 0 = DelayedOracle
SEL_LAST_UPDATE = "0xc8f33c91"  # lastUpdateTime() at the DelayedOracle
SEL_UPDATE_DELAY = "0x554f94db"  # updateDelay() at the DelayedOracle
SEL_REWARD = "0xf7b2a7be"       # rewardAmount() at the job
SEL_SLOT0 = "0x3850c7bd"        # slot0() at the pool

MIN_CLUSTER = 2                 # windows with fewer items belong to the single-item sibling bot
PRIO_WEI = 100_000_000          # 0.10 gwei bid
PRIO_MAX_SHARE = 0.50           # priority fee never above 50% of expected gross
MAX_FEE_CEIL = 110_000_000      # 0.11 gwei -> signed cap <= 950000 x 0.11 gwei = 1.045e-4 ETH (5 items)
L1_FEE_EST_WEI = 50_000_000_000  # 5e-8 ETH, >10x the OP L1 data fee seen on the fork sends (4.4e-9)
PRE_S = 15                      # quote / pre-check this long before due
CLUSTER_S = 3                   # items due within this many seconds form one window
SETTLE_S = 6                    # look for the taker this long after due
SAFETY_POLL_S = 600             # re-read the next window's lastUpdateTime while waiting
FULL_REFRESH_S = 3600           # re-read the whole schedule
STALE_S = 7200                  # an item overdue this long is not kept by anyone (bad feed): skip
LATE_BACKOFF_S = 600            # after a failed late attempt on a window
LEAD_INIT, LEAD_MIN, LEAD_MAX = 2.4, 1.6, 3.4   # send this long before due (signer ~1.25 s, 2 s blocks)
SIM_FROM = "0xb7f92bad6e6f400fafa85d6b61fa937b000000b0"  # {bot} of the fork-proof deployment (proof.py)
SIM_EXEC = "0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352"  # paper sim only (code override); never used live
RUNTIME = open(os.path.join(HERE, "executor-runtime.hex")).read().strip()
LEAD_FILE = os.path.join(HERE, "state", "lead.json")
sys.path.append("/opt/farm/lib")

# the kept collateral items (bytes32 ascii cTypes); the schedule decides which share a window
CTYPES = ["WETH", "WSTETH", "OP", "SNX", "RETH", "TBTC", "VELO",
          "HAIVELO", "HAIVELOV2", "MSETH", "HAIAERO", "MOO-VELO-BOLD-LUSD",
          "MOO-VELO-V2-OP-VELO", "YV-VELO-MSETH-WETH", "YV-VELO-ALETH-WETH"]


def gas_limit(n):
    # fork (proof.py): 5 items peak 870,173 gas before refunds (guard revert), 777,667 used
    # 2-item window (HAIAERO + MSETH): the jobs' gas varies by the hour; at the parent of block
    # 159639348 the whole path needed 563,705 gas (eth_estimateGas, scratch/.../gas2.py), so
    # small windows get a 700k floor.
    return max(300_000 + 130_000 * n, 700_000)


def gas_used_est(n):
    # used only to size the priority bid (<= 50% of gross at this much gas); for small windows
    # it is set above the heaviest measured use (563,705) so the share holds there too
    return 220_000 + 110_000 * n if n >= 4 else 600_000


def b32(name):
    return "0x" + name.encode().hex().ljust(64, "0")


def log(obj):
    obj = {"t": round(time.time(), 3), **obj}
    line = json.dumps(obj)
    print(line, flush=True)
    with open(os.path.join(HERE, "logs", "bot.jsonl"), "a") as f:
        f.write(line + "\n")


def rpc(method, params, timeout=20):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"{RELAY}/{CHAIN}?lane={LANE}", body, {"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    if "error" in r:
        raise RuntimeError(json.dumps(r["error"])[:300])
    return r["result"]


def call_words(to, data, min_words=1):
    """eth_call that must return at least min_words 32-byte words; one retry on a short answer."""
    for attempt in (0, 1):
        r = rpc("eth_call", [{"to": to, "data": data}, "latest"])
        if isinstance(r, str) and len(r) >= 2 + 64 * min_words:
            return r
        time.sleep(1)
    raise RuntimeError(f"short eth_call answer from {to} {data[:10]}: {str(r)[:40]}")


def word(hexstr, i):
    return int(hexstr[2 + 64 * i: 2 + 64 * (i + 1)], 16)


def enc_act(names, probe, min_items, min_profit, pool=POOL):
    # act(bytes32[] cTypes, address probe, address pool, uint256 minItems, uint256 minProfit)
    head = (format(0xa0, "064x") + probe[2:].lower().rjust(64, "0") + pool[2:].lower().rjust(64, "0")
            + format(min_items, "064x") + format(min_profit, "064x"))
    tail = format(len(names), "064x") + "".join(b32(n)[2:] for n in names)
    return SEL_ACT + head + tail


class Item:
    def __init__(self, name):
        self.name = name
        self.oracle = None
        self.delay = None
        self.last = None
        self.not_before = 0.0     # backoff after a failed late attempt
        self.stale_logged = False

    @property
    def due(self):
        return self.last + self.delay


def resolve(item):
    """Fill item.oracle / delay; a zero or malformed oracle address is never cached."""
    if item.oracle is None:
        r = call_words(RELAYER, SEL_CPARAMS + b32(item.name)[2:])
        orc = "0x" + r[26:66]
        if int(orc, 16) == 0:
            raise RuntimeError(f"cParams({item.name}) returned the zero oracle")
        delay = word(call_words(orc, SEL_UPDATE_DELAY), 0)
        if not 60 <= delay <= 7 * 86400:
            raise RuntimeError(f"updateDelay({item.name}) out of range: {delay}")
        item.oracle, item.delay = orc, delay
        log({"ev": "oracle_resolved", "cType": item.name, "oracle": orc, "update_delay_s": delay})


def read_last(item):
    resolve(item)
    item.last = word(call_words(item.oracle, SEL_LAST_UPDATE), 0)
    return item.last


def refresh(items):
    ok = 0
    for it in items:
        try:
            read_last(it)
            ok += 1
        except Exception as e:
            log({"ev": "resolve_err", "cType": it.name, "err": str(e)[:200]})
    return ok


def schedulable(items, now):
    out = []
    for it in items:
        if it.last is None:
            continue
        if it.due < now - STALE_S:
            if not it.stale_logged:
                log({"ev": "stale_item_skipped", "cType": it.name, "last_update": it.last, "overdue_s": int(now - it.due)})
                it.stale_logged = True
            continue
        it.stale_logged = False
        if it.not_before > now and it.due <= now:
            continue
        out.append(it)
    return out


def next_cluster(cand):
    """Earliest group of >= MIN_CLUSTER items due within CLUSTER_S of the group's first item."""
    cand = sorted(cand, key=lambda i: (i.due, i.name))
    i = 0
    while i < len(cand):
        grp = [c for c in cand[i:] if c.due - cand[i].due <= CLUSTER_S]
        if len(grp) >= MIN_CLUSTER:
            return grp
        i += len(grp)
    return None


def quote(reward):
    """Expected gross in wei for selling `reward` HAI on the pool at the current price (fee 0.3%)."""
    sqrtp = word(call_words(POOL, SEL_SLOT0), 0)
    gross = reward * sqrtp * sqrtp // (1 << 192) * 997 // 1000      # token1 (WETH) per token0 (HAI)
    blk = rpc("eth_getBlockByNumber", ["latest", False])
    return gross, int(blk.get("baseFeePerGas", "0x0"), 16), int(blk["timestamp"], 16), int(blk["number"], 16)


def fees(gross, base, n):
    prio = min(PRIO_WEI, int(PRIO_MAX_SHARE * gross / gas_used_est(n)))
    max_fee = min(MAX_FEE_CEIL, 2 * base + prio)
    return prio, max_fee, gas_limit(n) * max_fee


def load_lead():
    try:
        return min(LEAD_MAX, max(LEAD_MIN, float(json.load(open(LEAD_FILE))["lead_s"])))
    except Exception:
        return LEAD_INIT


def save_lead(v):
    try:
        os.makedirs(os.path.dirname(LEAD_FILE), exist_ok=True)
        json.dump({"lead_s": v}, open(LEAD_FILE, "w"))
    except Exception as e:
        log({"ev": "lead_save_err", "err": str(e)[:100]})


def sleep_until(ts):
    while True:
        d = ts - time.time()
        if d <= 0:
            return
        time.sleep(min(d, 30))


def wallet():
    import farmbot_signer
    a = farmbot_signer.my_address()          # {"ok": true, "address": "0x..."}
    a = a.get("address") if isinstance(a, dict) else a
    if not (isinstance(a, str) and len(a) == 42):
        raise RuntimeError("signer my_address gave no address")
    return a


def simulate(data, n, at_time=None):
    """Whole executor path at head (optionally with the block time set to `at_time`). Returns profit wei or raises."""
    if MODE == "live":
        tx = {"from": wallet(), "to": EXEC, "data": data, "gas": hex(gas_limit(n))}
        ov = {}
    else:
        tx = {"from": SIM_FROM, "to": SIM_EXEC, "data": data, "gas": hex(gas_limit(n))}
        ov = {SIM_EXEC: {"code": RUNTIME}}
    params = [tx, "latest"]
    if at_time is not None:
        params += [ov, {"time": hex(at_time)}]
    elif ov:
        params += [ov]
    res = rpc("eth_call", params)
    if not (isinstance(res, str) and len(res) >= 66):
        raise RuntimeError(f"short sim answer: {str(res)[:40]}")
    return int(res, 16)


def live_send(names, data, due, prio, max_fee, lead):
    import farmbot_signer
    n = len(names)
    t_send = time.time()
    r = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit(n), max_fee, max_priority_fee_per_gas=prio)
    t_reply = time.time()
    log({"ev": "sent", "items": names, "due": due, "send_wall_minus_due_s": round(t_send - due, 3),
         "signer_s": round(t_reply - t_send, 3), "lead_s": lead, "prio_gwei": prio / 1e9,
         "max_fee_gwei": max_fee / 1e9, "gas_cap_wei": gas_limit(n) * max_fee,
         "reply": json.dumps(r, default=str)[:300]})
    h = r.get("txHash") if isinstance(r, dict) else None
    if not h:
        return None          # a signer rejection is final: no retry
    for _ in range(20):
        time.sleep(1)
        try:
            rc = rpc("eth_getTransactionReceipt", [h])
        except Exception:
            rc = None
        if rc:
            blk = rpc("eth_getBlockByNumber", [rc["blockNumber"], False])
            ts = int(blk["timestamp"], 16)
            fee = int(rc["gasUsed"], 16) * int(rc["effectiveGasPrice"], 16) + int(rc.get("l1Fee", "0x0") or "0x0", 16)
            out = {"ev": "receipt", "items": names, "due": due, "tx": h, "status": int(rc["status"], 16),
                   "block": int(rc["blockNumber"], 16), "block_ts": ts, "landed_minus_due_s": ts - due,
                   "index": int(rc["transactionIndex"], 16), "gasUsed": int(rc["gasUsed"], 16),
                   "fee_wei": fee, "send_to_block_ts_s": round(ts - t_send, 3)}
            log(out)
            return out
    log({"ev": "no_receipt", "items": names, "due": due, "tx": h})
    return None


def find_taker(item, due, from_block):
    """Who updated this item's DelayedOracle after `from_block` (any log it emitted = the update)."""
    logs = rpc("eth_getLogs", [{"address": item.oracle, "fromBlock": hex(from_block), "toBlock": "latest"}])
    if not logs:
        return None
    lg = logs[0]
    h = lg["transactionHash"]
    rc = rpc("eth_getTransactionReceipt", [h])
    blk = rpc("eth_getBlockByNumber", [lg["blockNumber"], False])
    base = int(blk.get("baseFeePerGas", "0x0"), 16)
    egp = int(rc["effectiveGasPrice"], 16)
    return {"taker_tx": h, "taker_from": rc["from"], "taker_to": rc["to"], "taker_block": int(lg["blockNumber"], 16),
            "taker_block_ts": int(blk["timestamp"], 16), "taker_delay_s": int(blk["timestamp"], 16) - due,
            "taker_index": int(rc["transactionIndex"], 16), "taker_prio_gwei": round((egp - base) / 1e9, 6),
            "taker_gas_used": int(rc["gasUsed"], 16)}


def main():
    if MODE == "live" and not EXEC:
        log({"ev": "fatal", "msg": "EXECUTOR_ADDR unset"})
        sys.exit(1)
    os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
    lead = load_lead()
    items = [Item(c) for c in CTYPES]
    reward = None
    reward_at = 0.0
    last_full = 0.0
    log({"ev": "start", "mode": MODE, "executor": EXEC or "paper-sim-override", "items": len(items),
         "prio_gwei": PRIO_WEI / 1e9, "max_fee_ceil_gwei": MAX_FEE_CEIL / 1e9, "min_cluster": MIN_CLUSTER, "lead_s": lead})
    while True:
        try:
            now = time.time()
            if now - last_full > FULL_REFRESH_S:
                n_ok = refresh(items)
                last_full = time.time()
                log({"ev": "schedule", "resolved": n_ok,
                     "next": sorted([(it.due, it.name) for it in items if it.last is not None])[:16]})
                if n_ok == 0:
                    last_full = 0.0
                    time.sleep(60)
                    continue
            cluster = next_cluster(schedulable(items, time.time()))
            if not cluster:
                log({"ev": "no_cluster_window", "sleep_s": SAFETY_POLL_S})
                time.sleep(SAFETY_POLL_S)
                last_full = 0.0
                continue
            head_item = cluster[0]               # probe item: earliest due of the window
            due = max(it.due for it in cluster)  # every item of the window is due by then
            names = [it.name for it in cluster]
            n = len(names)
            log({"ev": "next_window", "due": due, "in_s": round(due - time.time(), 1), "items": names})
            # wait on the timer; a safety re-read every 10 min catches a changed schedule
            changed = False
            while time.time() < due - PRE_S:
                sleep_until(min(due - PRE_S, time.time() + SAFETY_POLL_S))
                if time.time() < due - PRE_S:
                    old = head_item.due
                    if read_last(head_item) + head_item.delay != old:
                        log({"ev": "schedule_changed", "cType": head_item.name, "old_due": old, "new_due": head_item.due})
                        changed = True
                        break
            if changed:
                last_full = 0.0
                continue
            if reward is None or time.time() - reward_at > 3600:
                reward = word(call_words(JOB, SEL_REWARD), 0)
                reward_at = time.time()
            gross, base, head_ts, head = quote(reward * n)
            prio, max_fee, cap = fees(gross, base, n)
            # send rule (trial decision section 1): expected gross > this send's signed gas cap (+ L1 data fee)
            go = gross > cap + L1_FEE_EST_WEI and (2 * base + prio) <= MAX_FEE_CEIL
            min_profit = cap + L1_FEE_EST_WEI + 1   # the executor enforces the same condition on-chain
            data = enc_act(names, head_item.oracle, n, min_profit)
            late = time.time() > due - lead         # started (or woke) too late for a timed send
            log({"ev": "window", "items": names, "due": due, "late": late, "reward_wad": reward * n,
                 "gross_est_wei": gross, "base_fee_wei": base, "prio_wei": prio, "max_fee_wei": max_fee,
                 "gas_limit": gas_limit(n), "gas_cap_wei": cap, "min_profit_wei": min_profit, "send": go,
                 "head": head, "head_ts": head_ts, "clock_minus_head_ts_s": round(time.time() - head_ts, 2)})
            receipt = None
            sim_ok = False
            if not go:
                log({"ev": "skip_gross_below_gas_cap", "items": names, "due": due})
            else:
                try:
                    if late:
                        # window already open: check the whole path at head, send at once if still untaken
                        if time.time() < due:
                            sleep_until(due + 2.5)
                        p = simulate(data, n)
                        log({"ev": "sim_ok", "at": "latest", "items": names, "due": due, "profit_wei": p})
                    else:
                        # pre-due check of the whole path at head with the block time set to `due`
                        p = simulate(data, n, at_time=due)
                        log({"ev": "sim_ok", "at": "latest+time_override", "items": names, "due": due, "profit_wei": p})
                    sim_ok = True
                except Exception as e:
                    log({"ev": "sim_revert", "at": "latest" if late else "latest+time_override",
                         "items": names, "due": due, "err": str(e)[:200]})
                if sim_ok and MODE == "live":
                    if not late:
                        sleep_until(due - lead)
                    receipt = live_send(names, data, due, prio, max_fee, lead)
            # who took it
            sleep_until(due + SETTLE_S)
            taker = None
            try:
                taker = find_taker(head_item, due, head - 5)
            except Exception as e:
                log({"ev": "taker_err", "err": str(e)[:200]})
            for it in cluster:
                try:
                    read_last(it)
                except Exception as e:
                    log({"ev": "reread_err", "cType": it.name, "err": str(e)[:200]})
            res = {"ev": "window_result", "items": names, "due": due, "mode": MODE, "late": late,
                   "our_prio_gwei": prio / 1e9, "sim_ok": sim_ok, "sent": receipt is not None,
                   "cluster_updated": {i.name: (i.last is not None and i.last >= due) for i in cluster}}
            if taker:
                res.update(taker)
            if MODE == "live":
                res["outcome"] = ("win" if receipt and receipt["status"] == 1 else
                                  "lose" if receipt else "not_sent_or_no_receipt")
                if receipt:
                    res["our_block"] = receipt["block"]
                    res["our_fee_wei"] = receipt["fee_wei"]
                    res["our_gas_used"] = receipt["gasUsed"]
                    if taker:
                        res["our_block_minus_taker_block"] = receipt["block"] - taker["taker_block"]
                    if not late:
                        # timer feedback: landed before due (probe NotDue) -> send later; after due -> earlier
                        if receipt["landed_minus_due_s"] < 0:
                            lead = max(LEAD_MIN, round(lead - 0.3, 2))
                        elif receipt["landed_minus_due_s"] > 0:
                            lead = min(LEAD_MAX, round(lead + 0.3, 2))
                        save_lead(lead)
                        res["next_lead_s"] = lead
            else:
                res["outcome"] = "paper"
                if taker:
                    res["would_outbid_taker"] = prio / 1e9 > taker["taker_prio_gwei"]
            log(res)
            for it in cluster:
                # still due after the window: do not spin on it; retry as a late window after a backoff
                if it.last is not None and it.due <= time.time():
                    it.not_before = max(it.not_before, time.time() + LATE_BACKOFF_S)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log({"ev": "err", "err": str(e)[:300]})
            time.sleep(60)


if __name__ == "__main__":
    main()
