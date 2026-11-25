#!/usr/bin/env python3
# trial-oraclejob-hai-optimism  (TRIAL bot, lead 211, decision 2026-11-17-cheap-chain-trials)
#
# HAI OracleJob on optimism pays 0.05 HAI (~0.062 USD) to anyone calling
# workUpdateCollateralPrice(cType) once per collateral item per hour. The time is known
# in advance: an item is due at DelayedOracle.lastUpdateTime() + updateDelay() (3600 s).
# The bot keeps the schedule of the 15 kept items, waits on a TIMER (no per-block or
# per-minute polling), and for each window (items due within CLUSTER_S of each other)
# sends ONE executor call for one item of the cluster (rotating), timed to land in the
# first block whose timestamp is >= due, with a small fixed priority bid. The executor
# does job -> CoinJoin.exit -> HAI/WETH UniV3 sell -> unwrap -> ETH to the wallet and
# reverts unless ETH out >= minProfit (= signed gas cap + L1 fee estimate + 1).
# Every window logs who took the item, in which block and at what priority fee, and for
# a live send: win/lose, gas used, our block minus the taker's block.
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
POOL = "0x146b020399769339509c98B7B353d19130C150EC"      # UniV3 HAI/WETH fee 3000, token0 = HAI

# selectors: all from `cast sig`
SEL_ACT = "0xb28e58c9"          # act(bytes32,uint256,uint256)
SEL_CPARAMS = "0xe54201f6"      # cParams(bytes32) at the OracleRelayer -> word 0 = DelayedOracle
SEL_LAST_UPDATE = "0xc8f33c91"  # lastUpdateTime() at the DelayedOracle
SEL_UPDATE_DELAY = "0x554f94db"  # updateDelay() at the DelayedOracle
SEL_REWARD = "0xf7b2a7be"       # rewardAmount() at the job
SEL_SLOT0 = "0x3850c7bd"        # slot0() at the pool

GAS_LIMIT = 500_000             # fork success used 341,269; guard revert 412,027
GAS_USED_EST = 369_000
PRIO_WEI = 30_000_000           # 0.03 gwei bid (~33% of gross at 369k gas)
PRIO_MAX_SHARE = 0.40           # priority fee never above 40% of expected gross
MAX_FEE_CEIL = 60_000_000       # 0.06 gwei -> signed cap <= 500000 x 0.06 gwei = 3e-5 ETH
L1_FEE_EST_WEI = 50_000_000_000  # 5e-8 ETH, 3x the largest OP L1 data fee seen on incumbent calls
PRE_S = 15                      # quote / pre-check this long before due
CLUSTER_S = 3                   # items due within this many seconds form one window
SETTLE_S = 6                    # look for the taker this long after due
SAFETY_POLL_S = 600             # re-read the next target's lastUpdateTime while waiting
FULL_REFRESH_S = 3600           # re-read the whole schedule
STALE_S = 7200                  # an item overdue this long is not kept by anyone (bad feed): skip
LATE_BACKOFF_S = 600            # after a failed late attempt on an item
LEAD_INIT, LEAD_MIN, LEAD_MAX = 2.4, 1.6, 3.4   # send this long before due (signer ~1.25 s, 2 s blocks)
SIM_FROM = "0x31babb54eaea4d73ad49455eed32f84c000000b0"  # {bot} of the fork-proof deployment (proof5.py, run 31babb54)
SIM_EXEC = "0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352"  # paper sim only (code override); never used live
RUNTIME = open(os.path.join(HERE, "executor-runtime.hex")).read().strip()
LEAD_FILE = os.path.join(HERE, "state", "lead.json")
sys.path.append("/opt/farm/lib")

# the 15 kept collateral items (bytes32 ascii cTypes)
CTYPES = ["WETH", "WSTETH", "OP", "SNX", "RETH", "TBTC", "VELO",
          "HAIVELO", "HAIVELOV2", "MSETH", "HAIAERO", "MOO-VELO-BOLD-LUSD",
          "MOO-VELO-V2-OP-VELO", "YV-VELO-MSETH-WETH", "YV-VELO-ALETH-WETH"]


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


def enc_act(name, min_profit):
    # act(bytes32 cType, uint256 minWethOut, uint256 minProfit); minProfit is the binding guard
    return SEL_ACT + b32(name)[2:] + format(1, "064x") + format(min_profit, "064x")


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


def quote(reward):
    """Expected gross in wei for selling the reward on the pool at the current price (fee 0.3%)."""
    sqrtp = word(call_words(POOL, SEL_SLOT0), 0)
    gross = reward * sqrtp * sqrtp // (1 << 192) * 997 // 1000      # token1 (WETH) per token0 (HAI)
    blk = rpc("eth_getBlockByNumber", ["latest", False])
    return gross, int(blk.get("baseFeePerGas", "0x0"), 16), int(blk["timestamp"], 16), int(blk["number"], 16)


def fees(gross, base):
    prio = min(PRIO_WEI, int(PRIO_MAX_SHARE * gross / GAS_USED_EST))
    max_fee = min(MAX_FEE_CEIL, 2 * base + prio)
    return prio, max_fee, GAS_LIMIT * max_fee


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


def simulate(name, min_profit, at_time=None):
    """Whole executor path at head (optionally with the block time set to `at_time`). Returns profit wei or raises."""
    if MODE == "live":
        tx = {"from": wallet(), "to": EXEC, "data": enc_act(name, min_profit), "gas": hex(GAS_LIMIT)}
        ov = {}
    else:
        tx = {"from": SIM_FROM, "to": SIM_EXEC, "data": enc_act(name, min_profit), "gas": hex(GAS_LIMIT)}
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


def live_send(name, due, min_profit, prio, max_fee, lead):
    import farmbot_signer
    t_send = time.time()
    r = farmbot_signer.send(CHAIN, EXEC, enc_act(name, min_profit), 0, GAS_LIMIT, max_fee,
                            max_priority_fee_per_gas=prio)
    t_reply = time.time()
    log({"ev": "sent", "cType": name, "due": due, "send_wall_minus_due_s": round(t_send - due, 3),
         "signer_s": round(t_reply - t_send, 3), "lead_s": lead, "prio_gwei": prio / 1e9,
         "max_fee_gwei": max_fee / 1e9, "gas_cap_wei": GAS_LIMIT * max_fee,
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
            out = {"ev": "receipt", "cType": name, "due": due, "tx": h, "status": int(rc["status"], 16),
                   "block": int(rc["blockNumber"], 16), "block_ts": ts, "landed_minus_due_s": ts - due,
                   "index": int(rc["transactionIndex"], 16), "gasUsed": int(rc["gasUsed"], 16),
                   "fee_wei": fee, "send_to_block_ts_s": round(ts - t_send, 3)}
            log(out)
            return out
    log({"ev": "no_receipt", "cType": name, "due": due, "tx": h})
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
    rot = 0
    reward = None
    reward_at = 0.0
    last_full = 0.0
    log({"ev": "start", "mode": MODE, "executor": EXEC or "paper-sim-override", "items": len(items),
         "prio_gwei": PRIO_WEI / 1e9, "gas_limit": GAS_LIMIT, "max_fee_ceil_gwei": MAX_FEE_CEIL / 1e9, "lead_s": lead})
    while True:
        try:
            now = time.time()
            if now - last_full > FULL_REFRESH_S:
                n = refresh(items)
                last_full = time.time()
                log({"ev": "schedule", "resolved": n,
                     "next": sorted([(it.due, it.name) for it in items if it.last is not None])[:16]})
                if n == 0:
                    last_full = 0.0
                    time.sleep(60)
                    continue
            cand = schedulable(items, time.time())
            if not cand:
                time.sleep(60)
                continue
            due = min(it.due for it in cand)
            cluster = sorted([it for it in cand if it.due - due <= CLUSTER_S], key=lambda i: i.name)
            target = cluster[rot % len(cluster)]
            due = target.due
            log({"ev": "next_window", "due": due, "in_s": round(due - time.time(), 1), "target": target.name,
                 "cluster": [i.name for i in cluster]})
            # wait on the timer; a safety re-read every 10 min catches a changed schedule
            changed = False
            while time.time() < due - PRE_S:
                sleep_until(min(due - PRE_S, time.time() + SAFETY_POLL_S))
                if time.time() < due - PRE_S:
                    if read_last(target) + target.delay != due:
                        log({"ev": "schedule_changed", "cType": target.name, "old_due": due, "new_due": target.due})
                        changed = True
                        break
            if changed:
                continue
            rot += 1
            if reward is None or time.time() - reward_at > 3600:
                reward = word(call_words(JOB, SEL_REWARD), 0)
                reward_at = time.time()
            gross, base, head_ts, head = quote(reward)
            prio, max_fee, cap = fees(gross, base)
            go = gross > cap + L1_FEE_EST_WEI and (2 * base + prio) <= MAX_FEE_CEIL
            min_profit = cap + L1_FEE_EST_WEI + 1   # executor reverts unless gross > signed gas cap + L1 data fee
            late = time.time() > due - lead         # started (or woke) too late for a timed send
            log({"ev": "window", "cType": target.name, "due": due, "late": late, "reward_wad": reward,
                 "gross_est_wei": gross, "base_fee_wei": base, "prio_wei": prio, "max_fee_wei": max_fee,
                 "gas_cap_wei": cap, "min_profit_wei": min_profit, "send": go, "head": head, "head_ts": head_ts,
                 "clock_minus_head_ts_s": round(time.time() - head_ts, 2)})
            receipt = None
            sim_ok = False
            if not go:
                log({"ev": "skip_gross_below_gas_cap", "cType": target.name, "due": due})
            else:
                try:
                    if late:
                        # window already open: check the whole path at head, send at once if still untaken
                        if time.time() < due:
                            sleep_until(due + 2.5)
                        p = simulate(target.name, min_profit)
                        log({"ev": "sim_ok", "at": "latest", "cType": target.name, "due": due, "profit_wei": p})
                    else:
                        # pre-due check of the whole path at head with the block time set to `due`
                        p = simulate(target.name, min_profit, at_time=due)
                        log({"ev": "sim_ok", "at": "latest+time_override", "cType": target.name, "due": due,
                             "profit_wei": p})
                    sim_ok = True
                except Exception as e:
                    log({"ev": "sim_revert", "at": "latest" if late else "latest+time_override",
                         "cType": target.name, "due": due, "err": str(e)[:200]})
                    if late:
                        target.not_before = time.time() + LATE_BACKOFF_S
                if sim_ok and MODE == "live":
                    if not late:
                        sleep_until(due - lead)
                    receipt = live_send(target.name, due, min_profit, prio, max_fee, lead)
            # who took it
            sleep_until(due + SETTLE_S)
            taker = None
            try:
                taker = find_taker(target, due, head - 5)
            except Exception as e:
                log({"ev": "taker_err", "err": str(e)[:200]})
            for it in cluster:
                try:
                    read_last(it)
                except Exception as e:
                    log({"ev": "reread_err", "cType": it.name, "err": str(e)[:200]})
            res = {"ev": "window_result", "cType": target.name, "due": due, "mode": MODE, "late": late,
                   "our_prio_gwei": prio / 1e9, "updated": target.last is not None and target.last >= due,
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
                        # timer feedback: landed before due (cooldown revert) -> send later; after due -> earlier
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
                # still due after the window: retry as a late window, but not in a tight loop
                if it.last is not None and it.due <= time.time():
                    it.not_before = max(it.not_before, time.time() + (LATE_BACKOFF_S if late else 60))
        except KeyboardInterrupt:
            break
        except Exception as e:
            log({"ev": "err", "err": str(e)[:300]})
            time.sleep(60)


if __name__ == "__main__":
    main()
