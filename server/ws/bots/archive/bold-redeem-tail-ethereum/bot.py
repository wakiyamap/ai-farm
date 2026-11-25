#!/usr/bin/env python3
# bold-redeem-tail-ethereum: Liquity V2 BOLD redemption tail-block bot (lead 117).
# Poll Redemption events at the 6 TroveManagers; when a burst has ended (its last
# block is behind head) run the executor once: Morpho WETH flash -> buy BOLD
# (UniV3 WETH/USDC + Curve-ng BOLD/USDC) -> CollateralRegistry.redeemCollateral ->
# sell wstETH/weETH -> repay -> revert unless WETH rose by minProfit; redeem()
# RETURNS the gross profit (uint256) so the bot can gate the send: it sends only
# when expected gross exceeds the signed gas cap (gasLimit x maxFeePerGas),
# because gas is paid in native while the guard checks a token balance.
# Paper mode simulates with eth_call + code override of the proven fork
# deployment at HEAD (state is live, code is the proof deployment); live sends
# via the signer. Review 2026-11-15 18:12Z fixes: (1) eth_call always carries
# from = the sender (owner) so the owner-only guard passes in live shape too;
# (2) send gate vs gas cap above; (3) 30 d per-occurrence table re-measured at
# landing blocks (scratch/bold-redeem-tail/sweep30d.py -> README windows30d.md).
# Review 2026-11-15 19:47Z (e64be614) fixes: (a) capture windows measured per
# occurrence at b_hi+1 and landing (scratch/bold-redeem-tail/sweep30d_v3.py ->
# table30d_v3.json, README windows section); (b) detector replay of the 30-day
# Redemption logs through this exact code (scratch/bold-redeem-tail/
# replay_detector.py); (c) the base-fee send gate below.
import json, os, sys, time, urllib.request, urllib.error

RELAY = os.environ.get("RPC_RELAY_URL", "http://127.0.0.1:8545")
LANE = os.environ.get("RPC_LANE", "paper")
MODE = os.environ.get("BOT_MODE", "paper")
CHAIN = "ethereum"
EXEC = os.environ.get("EXECUTOR_ADDR", "")
SIM_FROM = "0x1111111111111111111111111111111111111111"  # owner baked in the fork-deployed runtime
POLL_S = 10
MIN_BURST_BOLD = 5000 * 10**18
WETH_IN = 115 * 10**17
MIN_PROFIT = 5 * 10**14
COOLDOWN_S = 60
GAS_LIMIT = 1500000
MAX_FEE = 7 * 10**9           # 7 gwei signed cap
GAS_CAP_WEI = GAS_LIMIT * MAX_FEE  # 0.0105 ETH ~ 35 USD: send only when expected gross > this
sys.path.append("/opt/farm/lib")

MANAGERS = ["0x81d78814df42da2cab0e8870c477bc3ed861de66",
            "0xb47ef60132deabc89580fd40e49c062d93070046",
            "0xde026433882a9dded65cac4fff8402fafff40fca",
            "0x7bcb64b2c9206a5b699ed43363f6f98d4776cf5a",
            "0xa2895d6a3bf110561dfe4b71ca539d84e1928b22",
            "0xb2b2abeb5c357a234363ff5d180912d319e3e19e"]
TOPIC0 = "0x84ec8e1674d62e3a8ff294b1a7f53527d2d10291765fadf94e0ce431b2334334"

RUNTIME = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "executor-runtime.hex")).read().strip()

# executor address + code source per mode (paper: fork proof deployment 0x8f7a..
# with its runtime as override so head state is tested against proven code)
FORK_EXEC = "0x8f7a45ebde059392e46a46dcc14ab24681a961ea"

def log(obj):
    line = json.dumps(obj)
    print(line, flush=True)
    with open(os.path.join("logs", "bot.jsonl"), "a") as f:
        f.write(line + "\n")

def rpc(method, params, timeout=60):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"{RELAY}/{CHAIN}?lane={LANE}", body, {"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    if "error" in r:
        raise RuntimeError(json.dumps(r["error"])[:200])
    return r["result"]

# ---- redeem calldata (markets/route are call args, not baked) ----
SEL = "d67eb1f2"
UWP = "88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
WETH = "c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
BOLDUSDC = "efc6516323fbd28e80b85a497b65a86243a54b3e"
USDC = "a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
WSTP = "109830a1aaad605bbf02a9dfa7b0b92ec2fb7daa"
WSTETH = "7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0"
WEP = "553e9c493678d8606d6a5ba284643db2110df823"
WEETH = "ae78736cd615f374d3085123a210448e74fc6393"

def w(v): return f"{v:064x}"
def addr(a): return f"{int(a,16):064x}"
def leg(pool, sell, kind, i, j, zfo):
    return addr(pool)+addr(sell)+w(kind)+ (w(i if i>=0 else (1<<256)+i)) + (w(j if j>=0 else (1<<256)+j)) + w(1 if zfo else 0)

def redeem_calldata():
    buy = leg(UWP, WETH, 0, 0, 0, False) + leg(BOLDUSDC, USDC, 2, 1, 0, False)
    sell = leg(WSTP, WSTETH, 0, 0, 0, True) + leg(WEP, WEETH, 0, 0, 0, True)
    head = 4 * 32
    buy_at = head
    sell_at = buy_at + 32 + 2 * 192
    data = SEL + w(WETH_IN) + w(MIN_PROFIT) + w(buy_at) + w(sell_at)
    data += w(2) + buy
    data += w(2) + sell
    return "0x" + data

def wallet_address():
    if MODE != "live":
        return SIM_FROM
    import farmbot_signer
    a = farmbot_signer.my_address()
    return a["address"] if isinstance(a, dict) else a

def act(bold_total, blk_from, blk_to, from_addr):
    to = EXEC if MODE == "live" else FORK_EXEC
    tx = {"from": from_addr, "to": to, "data": redeem_calldata(), "gas": hex(GAS_LIMIT)}
    overrides = None if MODE == "live" else {to: {"code": RUNTIME}}
    t0 = time.time()
    try:
        res = rpc("eth_call", [tx, "latest"] + ([overrides] if overrides else []))
        gross = int((res or "0x0")[2:] or "0", 16)
        log({"ev": "sim_ok", "bold_in_burst": bold_total/1e18, "blocks": [blk_from, blk_to],
             "gross_eth": gross/1e18, "gas_cap_eth": GAS_CAP_WEI/1e18, "ms": int((time.time()-t0)*1000)})
        if gross <= GAS_CAP_WEI:
            log({"ev": "skip_below_gas_cap", "gross_eth": gross/1e18})
            return
        # fee gate (review round 3): the 30-day table shows the only
        # positive-gross landings sit on the redemption-rush day, where the
        # base fee spiked to 62-163 gwei while our signed cap is 7 gwei -
        # such a send would park in the mempool until fees collapse and then
        # execute on a tail-less state. Include only while base + 1 gwei
        # priority stays under the signed cap (1 extra read, send-time only).
        base = int(rpc("eth_getBlockByNumber", ["latest", False])["baseFeePerGas"], 16)
        if base + 10**9 > MAX_FEE:
            log({"ev": "skip_fee_gate", "gross_eth": gross/1e18, "baseFee_gwei": round(base/1e9, 2)})
            return
        if MODE == "live":
            try:
                import farmbot_signer
                r = farmbot_signer.send(CHAIN, EXEC, tx["data"], 0, GAS_LIMIT, MAX_FEE)
                log({"ev": "signer_reply", "reply": json.dumps(r, default=str)[:300]})
            except Exception as e2:
                log({"ev": "signer_err", "err": str(e2)[:150]})
    except Exception as e:
        log({"ev": "sim_revert", "bold_in_burst": bold_total/1e18, "blocks": [blk_from, blk_to], "err": str(e)[:150]})

def main():
    if MODE == "live" and not EXEC:
        log({"ev": "fatal", "msg": "EXECUTOR_ADDR unset"}); sys.exit(1)
    from_addr = wallet_address()
    head = int(rpc("eth_blockNumber", []), 16)
    cur_path = os.path.join("state", "cursor")
    cur = int(open(cur_path).read().strip()) if os.path.exists(cur_path) else head
    last_send = 0.0
    pending = {}  # block -> bold, redemption blocks seen but not yet finalized
    log({"ev": "start", "mode": MODE, "head": head, "cursor": cur, "from": from_addr,
         "exec": (EXEC or ("fork-override:" + FORK_EXEC)), "gas_cap_eth": GAS_CAP_WEI/1e18})
    while True:
        try:
            head = int(rpc("eth_blockNumber", []), 16)
            if head > cur:
                logs = rpc("eth_getLogs", [{"fromBlock": hex(cur + 1), "toBlock": hex(head),
                                            "address": MANAGERS, "topics": [TOPIC0]}])
                for l in logs:
                    b = int(l["blockNumber"], 16)
                    pending[b] = pending.get(b, 0) + int(l["data"][66:130], 16)
                cur = head
                open(cur_path, "w").write(str(cur))
                # group pending blocks into bursts (gaps <= 3 blocks); finalize
                # only groups whose last block is behind head (a tail exists).
                # A group ending at head stays pending: it may continue in the
                # next poll and must never be dropped (review fix #2).
                if pending:
                    blocks = sorted(pending)
                    groups, g = [], [blocks[0]]
                    for b in blocks[1:]:
                        if b - g[-1] <= 3:
                            g.append(b)
                        else:
                            groups.append(g); g = [b]
                    groups.append(g)
                    for gr in groups:
                        b_lo, b_hi = gr[0], gr[-1]
                        if b_hi >= head:
                            continue  # tail not confirmed yet
                        tot = sum(pending[b] for b in gr)
                        log({"ev": "burst", "blocks": [b_lo, b_hi], "bold": tot/1e18, "head": head})
                        if tot >= MIN_BURST_BOLD and time.time() - last_send > COOLDOWN_S:
                            last_send = time.time()
                            act(tot, b_lo, b_hi, from_addr)
                        for b in gr:
                            pending.pop(b, None)
        except Exception as e:
            log({"ev": "poll_err", "err": str(e)[:150]})
        time.sleep(POLL_S)

main()
