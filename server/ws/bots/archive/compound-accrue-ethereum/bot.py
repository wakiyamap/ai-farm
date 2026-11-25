#!/usr/bin/env python3
# compound-accrue-ethereum: Compound v2 accrueInterest caller-reward keeper (cETH).
# Watches the gap since the last cETH AccrueDistributed event on the comptroller;
# when the estimated accrued interest (gap x measured 1.95e-6 ETH/block) reaches
# DELTA_MIN, calls the executor's accrue(cToken, newSupplyRateMantissa, minProfit)
# which pays out only if the executor gained >= minProfit (revert -> gas only).
# Paper mode simulates with the pinned fork-proven executor code (eth_call override).
import json, os, sys, time, re, urllib.request, urllib.error, hashlib

MODE = os.environ.get("BOT_MODE", "paper")
RELAY = os.environ["RPC_RELAY_URL"]
LANE = os.environ.get("RPC_LANE", "paper")
CHAIN = "ethereum"
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
COMPTROLLER = "0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b"
ACCRUE_T0 = "0x2caecd17d02f56fa897705dcc740da2d237c373f70686f4e0d9bd3bf0400ea7a"
ACCRUAL_BLK_SEL = "6c540baf"  # cETH.accrualBlockNumber() measured live getter on the migrated layout (cast keccak + eth_call returned 26367304 at head 26368299, matches cETH storage slot 10; payout-0 accrues move this clock WITHOUT an AccrueDistributed event, measured: tx 0x92a8bce block 26365772 paid 0.00139 ETH with event word0=0 and accrualBlockNumber advanced to 26367304 at head)
RATE_PER_BLOCK = 1.95e-6  # ETH per block of accrued interest paid to callers at a supply-rate drift (measured 0.0818 ETH / 42000 blocks; the payout is utilization-driven: at the current stored utilization the payout is ~0 - measured head-fork payout bisect at gap ~1350 blocks ≈ 1e-18..1e-11 ETH, while payout accrues paid 0.009/0.0215 ETH at 337-582 block gaps; est_eth is only a trigger proxy)
STALE_MANTISSA = 45117721  # the stale mantissa keepers passed for weeks (measured: the payout winners' calldata mantissa 45117721 at txs 0x92a8bce/0x6fcdf3e8); fallback only when the live derived mantissa read fails
# fresh-rate multiplier (lead 93 recipe) REFUTED 2026-11-08: accrueInterest does NOT
# scale the payout with the caller-supplied mantissa - it VALIDATES the mantissa
# against the supply rate the contract derives from the same-block state (measured:
# at head mant 0/1 return accrue code 0 while 1000, the derived candidate 57507718,
# 1e8, 2e9 all return BAD_NEW_SUPPLY_RATE return code 9 = no accrue, no payout - the
# accrue "succeeds" on-chain and pays 0, so a live tx with an invalid mantissa costs
# gas only, the executor guard reverts NoProfit; scratch/compound-boundary-out.txt).
# The accrue path computes borrowRate = interestRateModel().getBorrowRate(getCash(),
# totalBorrows(), totalReserves()) (selector 15f24053; STATICCALL input words and the
# return 8322716640 in the keeper accrue trace, scratch/compound-accrue-trace.json,
# attempt 582) and derives the supply rate from the same utilization the caller must
# confirm. The trigger passes the same derived supply mantissa (supply_rate_mantissa).
CASH_SEL = "3b1d21a2"          # cETH.getCash() measured with cast sig (also readable at head; blocksPerYear()/utilization() revert from eth_call through "mint is paused" in the underlying guard)
BORROWS_SEL = "47bd3718"       # cETH.totalBorrows() measured with cast sig
MODEL_SEL = "f3fdb15a"         # cETH.interestRateModel() measured with cast sig (0xf9583618169920c544ec89795a346f487cb5a227 JumpRateModelV2 at head)
MODEL_BORROW_SEL = "15f24053"  # model.getBorrowRate(uint cash, uint borrows, uint reserves) measured from the accrue tx's STATICCALL input (scratch/compound-accrue-trace.json)
SUPPLY_RATE_SEL = "ae9d70b0"   # cETH.supplyRatePerBlock() measured at head 26371142 (returned 0, run 918ff617)
RESERVES_SEL = "8f840ddd"      # cETH.totalReserves() measured at head 26371142 (returned 0); re-read 2026-11-08T18:4xZ this session at head ~26371950: totalReserves 0x16cb48c172ffcf4e3 (1.326e18 > 0) while supplyRatePerBlock() still returned 0 - the lead-93 revival gate is reserves > 0 AND supplyRatePerBlock > 0 (half-open at this head: reserves positive, stored rate zero)
MIN_PROFIT_ETH = 0.0012   # executor minProfit: revert unless payout >= this. After-gas basis (review 2026-11-08T17:33Z: minProfit 0.0002 ETH was below the 0.00067 ETH gas exposure at 134642 gas x 5 gwei): the payout arrives to the executor before inclusion gas is deducted from its balance, so the wallet net is payout - gas; with the signed cap 200000 x 5 gwei = 0.001 ETH, minProfit 0.0012 ETH (about 2.7 USD at 2234 USD/ETH) guarantees net >= 0.0002 ETH after the worst-case signed gas. The trigger estimate threshold 0.002 ETH stays above it.
MIN_PROFIT_CAP = 10**16   # contract cap (constructor): minProfit <= 0.01 ETH
GAS_LIMIT = 200000        # measured accrue gasUsed 134642-145154
FEE_CAP_WEI = 5_000_000_000  # signed gas-fee cap 5 gwei (review 2026-11-08T08:07Z: the fixed 15 gwei cap = 200000 x 15 gwei = 0.003 ETH = $6.70 at the measured $2234/ETH exceeded the manifest's $5 bound; 200000 x 5 gwei = 0.001 ETH <= $5 at any signing price <= $5000/ETH - measured baseFeePerGas 0x212b3e3 = 0.035 gwei at block 26365772 with the winner keepers included well below the cap; the signer also enforces the farm L at the signing-time price)
POLL_BLOCKS = 30          # block cadence between checks (~6 min)
EXECUTOR_PAPER = "0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352"  # head-fork deployment of the payout contract (owner 0xf39f.. funded fork account, cap 1e16); runtime pinned in state/executor-code.hex
TRIG_GAP_BASE = 1000   # blocks (measured: accrual-clock gaps >= 1000 occurred 12 times in 7 d)
OWNER_PAPER = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"     # funded fork account used for paper simulation

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(STATE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def log(tag, **kw):
    line = json.dumps({"ts": int(time.time()), "kind": tag, **kw}, separators=(",", ":"))
    with open(os.path.join(LOG_DIR, "bot.jsonl"), "a") as f:
        f.write(line + "\n")

def http_json(url, payload, timeout=60):
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    if "error" in d:
        raise RuntimeError(str(d["error"])[:200])
    return d["result"]

RPC_ERRS = {"n": 0}
LAST_ERR = {"e": "", "kind": ""}  # last rpc failure: "evm" for JSON-RPC errors that carry an EVM revert, "transport" for relay/transport errors (review 06:32Z: the simulation must not label transport failures as reverts)
def rpc(method, params, lane=None):
    body = {"jsonrpc":"2.0","id":1,"method":method,"params":params}
    try:
        LAST_ERR["e"], LAST_ERR["kind"] = "", ""
        return http_json(f"{RELAY}/{CHAIN}?lane={lane or LANE}", body)
    except RuntimeError as e:
        # JSON-RPC error from the relay: an EVM revert carries "reverted"/the
        # revert string; anything else is a relay-side error, not a revert.
        s = str(e)[:300]
        RPC_ERRS["n"] += 1
        LAST_ERR["e"] = s
        LAST_ERR["kind"] = "evm" if ("reverted" in s or "NoProfit" in s or "execution" in s) else "relay_error"
        log("rpc_error", method=method, err=s[:200], evm_kind=LAST_ERR["kind"])
        return None
    except Exception as e:
        RPC_ERRS["n"] += 1
        LAST_ERR["e"], LAST_ERR["kind"] = str(e)[:300], "transport"
        log("rpc_error", method=method, err=str(e)[:200], kind="transport")
        return None

def hexint(x):
    return int(x, 16) if isinstance(x, str) and x.startswith("0x") else None

def accrue_calldata(param, minp):
    sel = "037b1e29"  # accrue(address,uint256,uint256) on the executor (cast keccak measured)
    return "0x" + sel + CETH[2:].rjust(64, "0") + format(param, "064x") + format(minp, "064x")

def last_ceth_accrue_block(head, cursor):
    # AccrueDistributed events with topic1=cETH in (cursor-6000, head]; returns
    # (last_block, [recent txhashes newest-first]) - txhashes feed the param recipe.
    lo = cursor - 6000
    body = {"fromBlock": hex(lo), "toBlock": hex(head),
            "address": COMPTROLLER,
            "topics": [ACCRUE_T0, "0x000000000000000000000000" + CETH[2:]]}
    logs = rpc("eth_getLogs", [body])
    if logs is None:
        return None
    if not logs:
        return None
    last = logs[-1]
    txs = [l["transactionHash"] for l in reversed(logs)]
    return hexint(last["blockNumber"]), txs

def winner_param(txhashes):
    # newSupplyRateMantissa from a recent accrueInterest call: batched keepers call it
    # through multicall routers (input 5f575529/174dea71/f0463878...), so the mantissa
    # lives in an internal call - trace the recent accrue txs and read the call to
    # cETH with selector db006a75. CU-heavy but only runs once per trigger (~1.7/day).
    for h in txhashes[:4]:
        tr = rpc("debug_traceTransaction", [h, {"tracer": "callTracer"}], lane="research")
        if not tr:
            continue
        stack = [tr]
        while stack:
            c = stack.pop()
            if c.get("to") == CETH and (c.get("input") or "")[:10] == "0xdb006a75":
                return int(c["input"][10:74], 16)
            stack.extend(c.get("calls", []) or [])
    return None

def accrual_blk():
    # cETH.accrualBlockNumber() - the on-chain accrual clock. Payout-0 accrues
    # advance it WITHOUT an AccrueDistributed event, so the gap (and the payout
    # estimate) must come from this getter, not from the event cursor.
    r = rpc("eth_call", [{"to": CETH, "data": "0x" + ACCRUAL_BLK_SEL}, "latest"])
    return hexint(r)


def ceth_gate():
    # lead 93 revival gate reads (re-read 2026-11-08T18:4xZ this session after the
    # relay state-read incident 17:1x-17:2xZ blocked the prior session's re-read,
    # inbox/meta/2026-11-08-relay-state-reads-empty.md): the payout leg is
    # zero for EVERY mantissa while cETH reserves/rate are degenerate (measured:
    # head 26371142 totalReserves 0 AND supplyRatePerBlock 0, run 918ff617; payout
    # dust 0-9 wei at head state for any caller). This session head ~26371950:
    # totalReserves 0x16cb48c172ffcf4e3 (1.326e18 > 0), supplyRatePerBlock() 0
    # (the stored rate only advances with an accrue; utilization ~ 590/48950 ETH).
    # Gate: reserves > 0 AND supplyRatePerBlock > 0; while closed, the bot skips the
    # trigger instead of burning gas on an accrue whose payout is capped at dust.
    rv = hexint(rpc("eth_call", [{"to": CETH, "data": "0x" + RESERVES_SEL}, "latest"]))
    sr = hexint(rpc("eth_call", [{"to": CETH, "data": "0x" + SUPPLY_RATE_SEL}, "latest"]))
    return rv, sr


def supply_rate_mantissa():
    # the caller-supplied supply mantissa the protocol validates: the accrue path
    # itself computes borrowRate = model.getBorrowRate(getCash(), totalBorrows(),
    # totalReserves()) and a supply rate from the same utilization; the caller must
    # confirm it (mantissa validated: attempt 582 + scratch/compound-boundary-out.txt
    # 2026-11-08: head 26372294 cash 2.143e22 borrows 1.512e20 reserves 2.628e19,
    # model borrowRate 8210735685, utilShare 70039665897458, derived supply 57507718;
    # at head only mant 0/1 returned accrue code 0, the candidate and every larger
    # mantissa returned 9 - the payout regime needs utilization freshness the accrue
    # block itself writes, same-block-fresh (the keeper mant 1e8 accrued at block
    # 26370275 validated only within its own block)). Returns the derived mantissa,
    # or None when a read fails (the caller then falls back to the observed mantissa).
    cash = hexint(rpc("eth_call", [{"to": CETH, "data": "0x" + CASH_SEL}, "latest"]))
    tb = hexint(rpc("eth_call", [{"to": CETH, "data": "0x" + BORROWS_SEL}, "latest"]))
    rv = hexint(rpc("eth_call", [{"to": CETH, "data": "0x" + RESERVES_SEL}, "latest"]))
    model = rpc("eth_call", [{"to": CETH, "data": "0x" + MODEL_SEL}, "latest"])
    model = (model or "").lower().replace("0x", "").lstrip("0")  # the getter returns the address padded to 32 bytes
    if cash is None or tb is None or rv is None or not re.match(r"^[0-9a-f]{40}$", model):
        return None
    model = "0x" + model
    br = hexint(rpc("eth_call", [{"to": model, "data": "0x" + MODEL_BORROW_SEL + "%064x" % cash + "%064x" % tb + "%064x" % rv}, "latest"]))
    if br is None or (cash + tb) == 0:
        return None
    util_share = tb * 10**16 // (tb + cash)
    return br * util_share // 10**16


def main():
    st = os.path.join(STATE_DIR, "state.json")
    state = json.load(open(st)) if os.path.exists(st) else {}
    cursor = state.get("cursor", None)
    executor = EXECUTOR_PAPER if MODE == "paper" else (os.environ.get("EXECUTOR_ADDR") or "").strip().lower()
    owner = OWNER_PAPER
    exec_code = None
    if MODE == "paper":
        p = os.path.join(STATE_DIR, "executor-code.hex")
        exec_code = open(p).read().strip() if os.path.exists(p) else None
    head = hexint(rpc("eth_blockNumber", []))
    last_check = 0
    # gap-block trigger with revert backoff: the payout is utilization-driven
    # (measured: 0.009/0.0215 ETH payouts at 337-582 block gaps, ~0 payout at the
    # current utilization with gap 1300 blocks), so a NoProfit-reverted trigger
    # must not repeat on the same state - double the gap threshold after every
    # revert (a reverted accrue leaves the accrual clock untouched), reset on success.
    trig_gap = state.get("trig_gap", TRIG_GAP_BASE)
    TRIG_GAP_CAP = 8000
    log("startup", mode=MODE, head=head, exec=executor or None, code_sha=hashlib.sha256((exec_code or "").encode()).hexdigest()[:12] if exec_code else None,
        cursor=cursor, trig_gap=trig_gap, min_profit=MIN_PROFIT_ETH, rate=RATE_PER_BLOCK, owner=owner)
    if executor and (exec_code or MODE == "live"):
        # fresh-rate probe: read the lead-93 revival gate first (reserves > 0 AND
        # supplyRatePerBlock > 0); while the gate is closed every mantissa pays 0
        # (measured head 26371142: reserves 0 and rate 0, payout 0-9 wei for any
        # caller/mantissa), so the probe reports the gate state and only simulates
        # the fresh mantissa when the gate is open (supply mantissa derived
        # at accrue time via supply_rate_mantissa(); measured head 26372294:
        # derived supply 57507718 while stored supplyRatePerBlock() 0).
        rv0, sr0 = ceth_gate()
        base0 = state.get("mantissa") or STALE_MANTISSA
        fresh0 = supply_rate_mantissa() or base0
        data0 = accrue_calldata(fresh0, int(MIN_PROFIT_ETH * 1e18))
        ov0 = {executor: {"code": exec_code}} if MODE == "paper" and exec_code else {}
        if not (rv0 and sr0):
            log("fresh_probe", base=base0, param=fresh0, gate=(rv0, sr0), sim="gate_closed")
        else:
            r0 = rpc("eth_call", [{"from": owner, "to": executor, "data": data0, "value": "0x0"}, "latest", ov0])
            log("fresh_probe", base=base0, param=fresh0, gate=(rv0, sr0), sim=("ok" if r0 is not None else ("revert" if LAST_ERR["kind"] == "evm" else "transport")), err=(LAST_ERR["e"][:120] if r0 is None else None))
    while True:
        head = hexint(rpc("eth_blockNumber", []))
        if head is None:
            time.sleep(30); continue
        if head - last_check < POLL_BLOCKS:
            time.sleep(12 * max(1, POLL_BLOCKS - (head - last_check)))
            continue
        last_check = head
        try:
            got = last_ceth_accrue_block(head, cursor or head - 6000)
        except Exception:
            got = None
        if got:
            b0, txh = got
            cursor = b0
        elif cursor is None:
            cursor = max(head - 6000, 0)
        ab = accrual_blk()
        gap = head - max(ab or 0, cursor or 0)
        est_eth = gap * RATE_PER_BLOCK
        fresh = state.get("supply_mantissa") or state.get("mantissa") or STALE_MANTISSA  # last derived supply mantissa (fallback: the mantissa observed on-chain)
        state.update({"cursor": cursor, "accrual_blk": ab, "head": head, "gap": gap, "est_eth": round(est_eth, 8), "fresh_mantissa": fresh})
        json.dump(state, open(st, "w"))
        log("heartbeat", head=head, cursor=cursor, accrual_blk=ab, gap=gap, est_eth=round(est_eth, 6), fresh_mantissa=fresh)
        if gap >= trig_gap:
            param = None
            if got:
                param = winner_param(txh)  # mantissa observed on a recent accrue tx (the stale-rate base)
            if param is None:
                param = state.get("mantissa")  # last mantissa observed on-chain
            stale_base = param or STALE_MANTISSA  # mantissa observed on-chain fallback (keepers' stale 45117721)
            if param is None:
                log("trigger_stale_fallback", base=stale_base, gap=gap, est_eth=round(est_eth, 6))
            fresh = supply_rate_mantissa() or stale_base  # protocol-valid supply mantissa derived from the same cash/borrows/reserves state the accrue path reads (supply_rate_mantissa; the fixed x184 fresh-rate recipe is REFUTED - mantissa validated against the same-block-derived supply rate, attempt 582 + scratch/compound-boundary-out.txt; fallback = observed mantissa, then stale 45117721)
            if param is not None:
                state["mantissa"] = param  # keep the observed on-chain base for the next round
            state["supply_mantissa"] = fresh
            json.dump(state, open(st, "w"))
            # lead-93 revival gate (re-read 2026-11-08T18:4xZ after the relay
            # state-read incident): the payout is dust (0-9 wei) for EVERY
            # mantissa while cETH reserves/rate are degenerate, so a trigger on
            # the gap proxy alone would only ever burn gas on NoProfit. Skip
            # (state untouched) unless reserves > 0 AND supplyRatePerBlock > 0.
            rv, sr = ceth_gate()
            if not (rv and sr):
                log("trigger_gate_closed", gap=gap, reserves=rv, supply_rate=sr)
                continue
            data = accrue_calldata(fresh, int(MIN_PROFIT_ETH * 1e18))
            sim = "error"
            if (MODE == "paper" and executor and exec_code) or (MODE == "live" and executor):
                # paper: simulate the executor call with its pinned fork-proven runtime
                # live: the same eth_call against the deployed executor proves the payout
                # on mainnet state; only then send through the signer (NoProfit reverts
                # would otherwise burn gas).
                overrides = {executor: {"code": exec_code}} if MODE == "paper" and exec_code else {}
                signer_send = None
                from_addr = owner
                if MODE == "live":
                    sys.path.insert(0, "/opt/farm/lib")
                    from farmbot_signer import send as signer_send, my_address
                    a = my_address()  # my_address returns the signer's whole response dict (review 2026-11-08T08:07Z: the dict must not leak into the from field)
                    from_addr = a.get("address") if isinstance(a, dict) else a
                    if not (isinstance(from_addr, str) and re.match(r"^0x[0-9a-fA-F]{40}$", from_addr)):
                        log("signer_address_error", resp=str(a)[:120])
                        from_addr = None
                if from_addr is None:
                    sim = "transport"  # signer address lookup failed: not a revert, try again next check
                else:
                    resp = rpc("eth_call", [{"from": from_addr, "to": executor, "data": data, "value": "0x0"}, "latest", overrides])
                    if resp is not None:
                        sim = "ok"
                    elif LAST_ERR["kind"] == "evm":
                        sim = "revert"  # a real EVM revert (NoProfit / accrue reverted)
                    else:
                        sim = "transport"  # relay or transport failure: not a revert, state unchanged
                log("simulate", gap=gap, est_eth=round(est_eth, 6), base=param, param=fresh, sim=sim, err=(LAST_ERR["e"][:120] if sim != "ok" else None))
                if sim == "revert":
                    # the accrue reverted (payout below minProfit at the current
                    # utilization): state is untouched, so only re-trigger once the
                    # gap doubles (a reverted accrue does not advance the clock).
                    trig_gap = min(trig_gap * 2, TRIG_GAP_CAP)
                    state["trig_gap"] = trig_gap
                    json.dump(state, open(st, "w"))
                if MODE == "live" and sim == "ok":
                    # signed gas-fee cap FEE_CAP_WEI (5 gwei): 200000 x 5 gwei =
                    # 0.001 ETH <= $5 at any signing price <= $5000/ETH (L;
                    # review 2026-11-08T08:07Z gas clamp); the signer also enforces
                    # L, allowed_contracts and the daily cap at the signing-time
                    # price, and a rejection is final (the bot exits, never retried in a loop).
                    r = signer_send(chain=CHAIN, to=executor, data=data, gas=GAS_LIMIT, max_fee_per_gas=FEE_CAP_WEI)
                    txh = (r or {}).get("txHash")
                    sim = "sent_pending" if (r or {}).get("ok") and txh else "rejected"
                    log("sent", gap=gap, param=fresh, ok=bool((r or {}).get("ok")), hash=txh, err=str((r or {}).get("error"))[:80])
                    if sim == "sent_pending":
                        # confirm the receipt before marking the opportunity captured
                        # (review 2026-11-08T08:07Z: a reverted or dropped tx must
                        # not be recorded as an accrue; keep the opportunity on failure)
                        rcpt = None
                        for _ in range(12):
                            rcpt = rpc("eth_getTransactionReceipt", [txh])
                            if rcpt is not None:
                                break
                            time.sleep(10)
                        ok_rcpt = bool(rcpt) and hexint(rcpt.get("status")) == 1
                        log("send_receipt", hash=txh, status=hexint(rcpt.get("status")) if rcpt else None, gap=gap)
                        if ok_rcpt:
                            sim = "sent"
                        else:
                            sim = "send_failed"  # reverted on-chain or dropped: opportunity unchanged, re-arm at a larger gap
                            trig_gap = min(trig_gap * 2, TRIG_GAP_CAP)
                            state["trig_gap"] = trig_gap
                            json.dump(state, open(st, "w"))
                    elif sim == "rejected":
                        break
            if sim in ("ok", "sent"):
                # a successful accrue resets the gap cursor to this block
                # and re-arms the trigger at the base gap threshold
                cursor = head
                trig_gap = TRIG_GAP_BASE
                state.update({"cursor": cursor, "last_accrue": head, "trig_gap": trig_gap})
                json.dump(state, open(st, "w"))
                log("accrued", mode=MODE, sim=sim, gap=gap, est_eth=round(est_eth, 6), min_profit_eth=MIN_PROFIT_ETH)
        time.sleep(2)

if __name__ == "__main__":
    main()
