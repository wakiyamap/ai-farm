#!/usr/bin/env python3
# trial-updaterate-hai-optimism  (TRIAL bot, decision 2026-11-17-cheap-chain-trials)
#
# HAI (GEB fork on OP Mainnet) pays rewardAmount (0.05 HAI) to anyone who calls
# OracleJob.workUpdateRate() once the PIDRateSetter cooldown (3600 s) has passed.
# The time is known in advance: due = PIDRateSetter.lastUpdateTime() + updateRateDelay.
# This bot waits on a timer (no per-block polling), sends ONE executor call timed to
# land in the first block whose timestamp is >= due, bidding a small fixed priority fee,
# and logs for every window who took it, in which block and at what priority fee.
#
# paper: sends nothing; simulates the executor (code override of the fork deployment,
#        block time overridden to `due`) and records the taker of every window.
# live : one signer send per window, only if expected gross > the signed gas cap.
import json, os, sys, time, urllib.request

RELAY = os.environ.get("RPC_RELAY_URL", "http://127.0.0.1:8545")
LANE = os.environ.get("RPC_LANE", "paper")
MODE = os.environ.get("BOT_MODE", "paper")
EXEC = os.environ.get("EXECUTOR_ADDR", "")
CHAIN = "optimism"
HERE = os.path.dirname(os.path.abspath(__file__))

JOB = "0xF4F18205D8D46638489865e42c0a71a3d4F9FC22"         # HAI OracleJob
RATESETTER = "0x1f76f20c9d9075dc160d0e47cd214df0b7434d2f"  # JOB.pidRateSetter()
RELAYER = "0x6270403b908505f02da05be5c1956abb59fdb3a6"     # JOB.oracleRelayer(), emits UpdateRedemptionRate
POOL = "0x146b020399769339509c98B7B353d19130C150EC"        # UniV3 HAI/WETH fee 3000, token0 = HAI

# selectors / topics: all from `cast sig` / `cast keccak` (scratch/trial-updaterate-hai/selectors.txt)
SEL_ACT = "0x2fc9e7e9"            # act(bytes,address,uint256)
SEL_WORK_UPDATE_RATE = "0xdbbb74d5"  # workUpdateRate()
SEL_LAST_UPDATE = "0xc8f33c91"      # lastUpdateTime()
SEL_PARAMS = "0xcff0ab96"           # params() -> updateRateDelay
SEL_REWARD = "0xf7b2a7be"           # rewardAmount()
SEL_SLOT0 = "0x3850c7bd"            # slot0()
T_RATE = "0x1bdc32c630331e3a9eb8dbcfab92261c58f8565d3c9ebac7f532a78ca07d61de"  # UpdateRedemptionRate(uint256)

GAS_LIMIT = 600_000              # fork success used 439,836
GAS_USED_EST = 440_000
PRIO_WEI = 10_000_000            # 0.01 gwei bid
PRIO_MAX_SHARE = 0.15            # priority fee never above 15% of expected gross
MAX_FEE_CEIL = 30_000_000        # 0.03 gwei -> signed cap <= 600000 x 0.03 gwei = 1.8e-5 ETH
L1_FEE_EST_WEI = 50_000_000_000  # 5e-8 ETH: 3x the largest OP L1 data fee seen on incumbent calls (1.6e-8)
PRE_S = 20                      # quote / decide this long before due
SAFETY_POLL_S = 600
SIM_FROM = "0xda0fc135f62044819f3f6b47f54d7417000000b0"   # {bot} of the fork-proof deployment
SIM_EXEC = "0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352"   # paper sim only (code override); never used live
RUNTIME = open(os.path.join(HERE, "executor-runtime.hex")).read().strip()
LEAD_FILE = os.path.join(HERE, "state", "lead.json")
sys.path.append("/opt/farm/lib")


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


def call(to, data):
    return rpc("eth_call", [{"to": to, "data": data}, "latest"])


def word(hexstr, i):
    return int(hexstr[2 + 64 * i: 2 + 64 * (i + 1)], 16)


def enc_act(min_profit):
    # act(bytes jobCall, address pool, uint256 minProfit): head = offset(0x60), pool, minProfit; tail = len 4 + data
    return (SEL_ACT + format(0x60, "064x") + POOL[2:].lower().rjust(64, "0") + format(min_profit, "064x")
            + format(4, "064x") + SEL_WORK_UPDATE_RATE[2:].ljust(64, "0"))


def read_due():
    last = int(call(RATESETTER, SEL_LAST_UPDATE), 16)
    delay = word(call(RATESETTER, SEL_PARAMS), 0)
    return last, last + delay


def quote():
    """Expected gross in wei for selling the reward on the pool at the current price (fee 0.3%)."""
    reward = int(call(JOB, SEL_REWARD), 16)
    sqrtp = word(call(POOL, SEL_SLOT0), 0)
    gross = reward * sqrtp * sqrtp // (1 << 192) * 997 // 1000      # token1 (WETH) per token0 (HAI)
    blk = rpc("eth_getBlockByNumber", ["latest", False])
    return reward, gross, int(blk.get("baseFeePerGas", "0x0"), 16), int(blk["timestamp"], 16), int(blk["number"], 16)


def fees(gross, base):
    prio = min(PRIO_WEI, int(PRIO_MAX_SHARE * gross / GAS_USED_EST))
    max_fee = min(MAX_FEE_CEIL, 2 * base + prio)
    return prio, max_fee, GAS_LIMIT * max_fee


def load_lead():
    try:
        return float(json.load(open(LEAD_FILE))["lead_s"])
    except Exception:
        return 1.0


def save_lead(v):
    try:
        json.dump({"lead_s": v}, open(LEAD_FILE, "w"))
    except Exception as e:
        log({"ev": "lead_save_err", "err": str(e)[:100]})


def sleep_until(ts):
    while True:
        d = ts - time.time()
        if d <= 0:
            return
        time.sleep(min(d, 30))


def find_taker(due, from_block):
    """Who took the window: UpdateRedemptionRate log at the OracleRelayer after `from_block`."""
    logs = rpc("eth_getLogs", [{"address": RELAYER, "topics": [T_RATE], "fromBlock": hex(from_block), "toBlock": "latest"}])
    if not logs:
        return None
    lg = logs[0]
    h = lg["transactionHash"]
    tx = rpc("eth_getTransactionByHash", [h])
    rc = rpc("eth_getTransactionReceipt", [h])
    blk = rpc("eth_getBlockByNumber", [lg["blockNumber"], False])
    base = int(blk.get("baseFeePerGas", "0x0"), 16)
    egp = int(rc["effectiveGasPrice"], 16)
    return {"taker_tx": h, "taker_from": tx["from"], "taker_to": tx["to"], "taker_block": int(lg["blockNumber"], 16),
            "taker_block_ts": int(blk["timestamp"], 16), "taker_delay_s": int(blk["timestamp"], 16) - due,
            "taker_index": int(rc["transactionIndex"], 16), "taker_prio_gwei": round((egp - base) / 1e9, 6),
            "taker_gas_used": int(rc["gasUsed"], 16)}


def paper_sim(due, min_profit):
    tx = {"from": SIM_FROM, "to": SIM_EXEC, "data": enc_act(min_profit), "gas": hex(GAS_LIMIT)}
    ov = {SIM_EXEC: {"code": RUNTIME}}
    try:
        res = rpc("eth_call", [tx, "latest", ov, {"time": hex(due)}])
        log({"ev": "sim_ok", "at": "latest+time_override", "due": due, "profit_wei": int(res, 16), "min_profit_wei": min_profit})
        return
    except Exception as e:
        log({"ev": "sim_revert", "at": "latest+time_override", "due": due, "err": str(e)[:200]})


def live_send(due, min_profit, prio, max_fee, lead):
    import farmbot_signer
    t_send = time.time()
    r = farmbot_signer.send(CHAIN, EXEC, enc_act(min_profit), 0, GAS_LIMIT, max_fee, max_priority_fee_per_gas=prio)
    t_reply = time.time()
    log({"ev": "sent", "due": due, "send_wall_minus_due_s": round(t_send - due, 3), "signer_s": round(t_reply - t_send, 3),
         "lead_s": lead, "prio_gwei": prio / 1e9, "max_fee_gwei": max_fee / 1e9, "gas_cap_wei": GAS_LIMIT * max_fee,
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
            out = {"ev": "receipt", "due": due, "tx": h, "status": int(rc["status"], 16), "block": int(rc["blockNumber"], 16),
                   "block_ts": ts, "landed_minus_due_s": ts - due, "index": int(rc["transactionIndex"], 16),
                   "gasUsed": int(rc["gasUsed"], 16), "fee_wei": fee, "send_to_block_ts_s": round(ts - t_send, 3)}
            log(out)
            return out
    log({"ev": "no_receipt", "due": due, "tx": h})
    return None


def main():
    if MODE == "live" and not EXEC:
        log({"ev": "fatal", "msg": "EXECUTOR_ADDR unset"})
        sys.exit(1)
    lead = load_lead()
    log({"ev": "start", "mode": MODE, "executor": EXEC or "paper-sim-override", "prio_gwei": PRIO_WEI / 1e9,
         "gas_limit": GAS_LIMIT, "max_fee_ceil_gwei": MAX_FEE_CEIL / 1e9, "lead_s": lead})
    while True:
        try:
            last, due = read_due()
            now = time.time()
            log({"ev": "next_window", "last_update": last, "due": due, "in_s": round(due - now, 1)})
            # wait on the timer; a safety re-read every 10 min catches a changed schedule
            changed = False
            while time.time() < due - PRE_S:
                sleep_until(min(due - PRE_S, time.time() + SAFETY_POLL_S))
                if time.time() < due - PRE_S:
                    l2, d2 = read_due()
                    if d2 != due:
                        log({"ev": "schedule_changed", "old_due": due, "new_due": d2})
                        changed = True
                        break
            if changed:
                continue
            late = time.time() > due + 1      # started (or woke) after the window opened
            reward, gross, base, head_ts, head = quote()
            prio, max_fee, cap = fees(gross, base)
            go = gross > cap + L1_FEE_EST_WEI and (2 * base + prio) <= MAX_FEE_CEIL
            log({"ev": "window", "due": due, "late": late, "reward_wad": reward, "gross_est_wei": gross, "base_fee_wei": base,
                 "prio_wei": prio, "max_fee_wei": max_fee, "gas_cap_wei": cap, "send": go,
                 "head": head, "head_ts": head_ts, "clock_minus_head_ts_s": round(time.time() - head_ts, 2)})
            min_profit = cap + L1_FEE_EST_WEI + 1   # executor reverts unless gross > signed gas cap + L1 data fee
            receipt = None
            if MODE == "live":
                if go:
                    if late:
                        # window already open and untaken: check at head, then send at once
                        try:
                            res = rpc("eth_call", [{"from": json_addr(), "to": EXEC, "data": enc_act(min_profit),
                                                    "gas": hex(GAS_LIMIT)}, "latest"])
                            log({"ev": "sim_ok", "at": "latest", "profit_wei": int(res, 16)})
                            receipt = live_send(due, min_profit, prio, max_fee, lead)
                        except Exception as e:
                            log({"ev": "sim_revert", "at": "latest", "err": str(e)[:200]})
                    else:
                        # pre-due check of the whole path at head with the block time set to `due`
                        try:
                            res = rpc("eth_call", [{"from": json_addr(), "to": EXEC, "data": enc_act(min_profit),
                                                    "gas": hex(GAS_LIMIT)}, "latest", {}, {"time": hex(due)}])
                            log({"ev": "sim_ok", "at": "latest+time_override", "due": due, "profit_wei": int(res, 16)})
                            sleep_until(due - lead)
                            receipt = live_send(due, min_profit, prio, max_fee, lead)
                        except Exception as e:
                            log({"ev": "sim_revert", "at": "latest+time_override", "due": due, "err": str(e)[:200]})
                else:
                    log({"ev": "skip_gross_below_gas_cap", "due": due})
            else:
                paper_sim(due, min_profit)
                # sequencer timing: when does the first block with ts >= due become visible?
                sleep_until(due - 1.5)
                for _ in range(14):
                    b = rpc("eth_getBlockByNumber", ["latest", False])
                    if int(b["timestamp"], 16) >= due:
                        log({"ev": "due_block_seen", "due": due, "block": int(b["number"], 16), "block_ts": int(b["timestamp"], 16),
                             "seen_wall_minus_due_s": round(time.time() - due, 3)})
                        break
                    time.sleep(0.5)
            # who took it
            sleep_until(due + 8)
            taker = None
            try:
                taker = find_taker(due, head - 5)
            except Exception as e:
                log({"ev": "taker_err", "err": str(e)[:200]})
            res = {"ev": "window_result", "due": due, "mode": MODE, "our_prio_gwei": prio / 1e9}
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
                    # timer feedback: early (cooldown revert before due) -> send later; late -> send earlier
                    if receipt["landed_minus_due_s"] < 0:
                        lead = max(0.2, lead - 0.3)
                    elif receipt["landed_minus_due_s"] > 0:
                        lead = min(1.9, lead + 0.2)
                    save_lead(lead)
                    res["next_lead_s"] = lead
            else:
                res["outcome"] = "paper"
                if taker:
                    res["would_outbid_taker"] = prio / 1e9 > taker["taker_prio_gwei"]
            log(res)
            if not taker:
                # nobody took it within 8 s: the next loop sees the same due as a late window
                time.sleep(30)
        except KeyboardInterrupt:
            break
        except Exception as e:
            log({"ev": "err", "err": str(e)[:300]})
            time.sleep(60)


def json_addr():
    import farmbot_signer
    a = farmbot_signer.my_address()
    return a.get("address") if isinstance(a, dict) else a


if __name__ == "__main__":
    main()
