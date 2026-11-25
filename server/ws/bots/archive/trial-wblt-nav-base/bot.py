#!/usr/bin/env python3
"""trial: wBLT (BMX's wrapped BLT, a Yearn-style vault share over the staked BLT liquidity token of BMX's GMX-style
vault on Base) can be minted and redeemed by anyone at the vault's price:
  mint:   RewardRouter.mintAndStakeGlp(USDC) -> staked BLT, wBLT.deposit
  redeem: wBLT.withdraw -> staked BLT, RewardRouter.unstakeAndRedeemGlp -> USDC
(cooldownDuration is 0, so both run inside one transaction). wBLT also trades against BNKR on a Uniswap v4 pool with
a custom-curve hook. When BNKR or the pool moves, the round trip
  redeem: USDC -> WETH -> BNKR (two V3-style pools) -> wBLT (v4), withdraw, unstakeAndRedeemGlp -> USDC
  mint:   USDC -> mintAndStakeGlp, deposit -> wBLT -> BNKR (v4) -> WETH -> USDC
pays. One transaction through the NavVaultArb executor with a free Morpho flash loan of USDC; it reverts unless its
USDC balance grew by minProfit, and sends all USDC to the bot wallet. No principal.
Timer bot: the hook pool keeps no price in the pool manager, so the screen is the executor's own quote() (always
reverts, gain in the revert data) for both directions and two sizes, through Multicall3: ONE eth_call every POLL
seconds. The exact run() is simulated only when a quote shows a gain above MIN_INTEREST."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545').rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'base'

# Addresses: from the incumbent's call traces (tx 0xda5e6715ded3..., 0x13d958ca88a4...); each answered the getter that
# names its neighbour on 2026-11-22 (scratch/trial-wblt-nav-base/getters.py; the proof script repeats the checks).
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
ROUTER = '0x49a97680938b4f1f73816d1b70c3ab801fad124b'     # BMX RewardRouter: mintAndStakeGlp / unstakeAndRedeemGlp
MANAGER = '0x9fac7b75f367d5b35a6d6d0a09572efcc3d406c5'    # = ROUTER.glpManager(): spender of USDC on a mint
STAKED = '0x64755939a80bc89e1d2d0f93a312908d348bc8de'     # = wBLT.token(): transferable staked BLT
WBLT = '0x4e74d4db6c0726ccded4656d0bce448876bb4c7a'       # wrapper vault share
BNKR = '0x22af33fe49fd1fa80c7149773dde5890d3c76f3b'
POOL_A = '0xb2cc224c1c9fee385f8ad6a55b4d94e92359dc59'     # V3-style WETH / USDC
POOL_B = '0xaec085e5a5ce8d96a7bdd3eb3a62445d4f6ce703'     # V3-style BNKR / WETH
V4_FEE, V4_TS = 8000, 1                                   # v4 pool BNKR / wBLT ...
V4_HOOK = '0x95afbc0fccf974b41380f24e562f15b6dd90fac8'    # ... with this hook (custom curve; pool key from the traces)
PM = '0x498581ff718922c3f8e6a244956af099b2652b2b'         # Uniswap v4 PoolManager
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'     # Morpho Blue: flashLoan, no fee
MULTICALL3 = '0xca11bde05977b3631167028862be2a173976ca11'

# Selectors and topics from `cast sig` / `cast keccak` (scratch/trial-wblt-nav-base/build.py, 2026-11-22).
SEL_RUN = '0x76a62ec2'      # run((address,address,address,address,address,address,address,address,address,address,uint24,int24,address,bool,uint256,uint256))
SEL_QUOTE = '0xb388e1e2'    # quote((same struct))
ERR_QUOTE = '44c8ad13'      # Quote(uint256)
SEL_AGG3 = '0x82ad56cb'     # aggregate3((address,bool,bytes)[])
TOPIC_TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
ZERO_TOPIC = '0x' + '0' * 64

PAPER_EXEC = '0x00000000000000000000000000000000000b17a5'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

POLL = 30                          # seconds between looks (one eth_call each)
SCREEN_SIZES = [20, 50]            # USDC sizes quoted for both directions in the look's one call (the hook pool is thin:
                                   # incumbents take about 30 USDC a time, and 120 USDC showed no gain where 30 did)
SIZES = [10, 20, 30, 45, 60, 90]   # sizes quoted (one more call) for the direction that showed a gain
MIN_INTEREST = 30_000              # 0.03 USDC: smaller gains are not worth a send
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send when gross > 1.3 x the send's gas cap
TIP_SHARE_DEN = 10                 # priority fee: at most 1/10 of gross spread over the gas limit ...
TIP_MAX_WEI = 8 * 10**7            # ... and never above 0.08 gwei
MAX_FEE_CAP_WEI = 11 * 10**7       # never sign above 0.11 gwei
GAS_LIMIT_MAX = 3_200_000          # 3.2M x 0.11 gwei = 0.000352 ETH = 0.88 USD at the reference price
L1_FEE_ALLOW_WEI = 2 * 10**12      # allowance for the OP Stack L1 data fee (incumbent takes: under 1e-8 ETH)
ETH_REF_USD = 2500.0               # USD cap reference, well above the price (about 1,710 USD on 2026-11-22)
MAX_TX_USD = 0.95
CU_CAP = 95_000
CU_COST = {'eth_call': 26, 'eth_getBlockByNumber': 20, 'eth_estimateGas': 20,
           'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10, 'eth_getLogs': 75}

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'cu.json'


class ReadBudgetExceeded(Exception):
    pass


def log(event, **fields):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': round(time.time(), 3), 'ev': event, **fields}, separators=(',', ':')) + '\n')


def rpc(method, params, raw=False):
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(STATE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    budget['cu'] += CU_COST.get(method, 26)
    if budget['cu'] > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} CU/day cap')
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(budget))
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    import urllib.request
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as resp:
        ans = json.load(resp)
    if raw:
        return ans
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:300]}')
    return ans['result']


def w(n):
    return format(n, '064x')


def a(addr):
    return addr.lower().removeprefix('0x').zfill(64)


def struct_words(mint, amount, min_profit):
    return ''.join([a(MORPHO), a(PM), a(ROUTER), a(MANAGER), a(STAKED), a(WBLT), a(USDC), a(BNKR), a(POOL_A), a(POOL_B),
                    w(V4_FEE), w(V4_TS), a(V4_HOOK), w(1 if mint else 0), w(amount), w(min_profit)])


def run_calldata(mint, amount, min_profit):
    return SEL_RUN + struct_words(mint, amount, min_profit)


def quote_calldata(mint, amount):
    return SEL_QUOTE + struct_words(mint, amount, 0)


# ---- chain access ----
def owner():
    import farmbot_signer
    result = farmbot_signer.my_address()
    address = result['address'] if isinstance(result, dict) else result
    if not isinstance(address, str) or len(address) != 42:
        raise RuntimeError('signer my_address returned no address')
    return address


def executor():
    return EXEC if MODE == 'live' else PAPER_EXEC


def with_override(params):
    if MODE == 'paper':
        params.append({executor(): {'code': RUNTIME_FILE.read_text().strip()}})
    return params


def quotes(pairs, block='latest'):
    """One eth_call: Multicall3.aggregate3 of executor.quote() for every (mint, USDC size) pair, failures allowed.
    quote() always reverts; a Quote(gain) revert carries the gain, any other revert (the loan could not be repaid)
    counts as 0. Returns the gains in USDC units, in order."""
    ex = executor()
    items = []
    for mint, size in pairs:
        raw = quote_calldata(mint, size * 10**6).removeprefix('0x')
        items.append(a(ex) + w(1) + w(0x60) + w(len(raw) // 2) + raw + '00' * ((-(len(raw) // 2)) % 32))
    offs, pos = [], 32 * len(items)
    for it in items:
        offs.append(pos)
        pos += len(it) // 2
    data = SEL_AGG3 + w(32) + w(len(items)) + ''.join(w(o) for o in offs) + ''.join(items)
    res = rpc('eth_call', with_override([{'to': MULTICALL3, 'data': data}, block])).removeprefix('0x')
    n = int(res[64:128], 16)
    if n != len(pairs):
        raise RuntimeError('aggregate3: unexpected return length')
    base = 128
    out = []
    for i in range(n):
        off = int(res[base + 64 * i:base + 64 * (i + 1)], 16) * 2 + base
        ln = int(res[off + 128:off + 192], 16) * 2
        ret = res[off + 192:off + 192 + ln]
        out.append(int(ret[8:72], 16) if ret[:8] == ERR_QUOTE and len(ret) >= 72 else 0)
    return out


def call_params(data, gas_limit=None, block='latest'):
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': executor(), 'data': data}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    return with_override([tx, block])


def gain_of(mint, amount, min_profit, gas_limit=None, block='latest'):
    """Return value of the exact run() as an eth_call (USDC units gained); 0 when it reverts."""
    ans = rpc('eth_call', call_params(run_calldata(mint, amount, min_profit), gas_limit, block), raw=True)
    if 'error' in ans or not ans.get('result') or ans['result'] == '0x':
        return 0, str(ans.get('error'))[:160]
    return int(ans['result'], 16), None


def best_size(mint, block='latest'):
    """Quote every size of SIZES for one direction in one call; returns (amount in USDC units, gain)."""
    gains = quotes([(mint, s) for s in SIZES], block)
    i = max(range(len(SIZES)), key=lambda k: gains[k])
    return SIZES[i] * 10**6, gains[i]


def last_take_block(block):
    """Block of the newest wBLT mint or burn near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': WBLT, 'fromBlock': hex(block - 300), 'toBlock': hex(block + 10), 'topics': [TOPIC_TRANSFER]}])
    hits = [int(x['blockNumber'], 16) for x in logs if ZERO_TOPIC in x['topics'][1:3]]
    return max(hits, default=None)


def send_live(mint, amount, gross, cap_usdc, max_fee, tip, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, run_calldata(mint, amount, cap_usdc), 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', reply=reply)
        return
    receipt = None
    for _ in range(20):
        time.sleep(1.0)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    common = dict(hash=tx_hash, mint=mint, amount_usdc=amount, expected_gross_usdc=gross,
                  cap_usdc=cap_usdc, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee') or '0x0', 16)
    try:
        winner = block if status else last_take_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        gross_usdc=gross if status else 0, send_block=block, winner_block=winner,
        tx_index=int(receipt['transactionIndex'], 16), **common)


_last = {}    # direction -> the screen gains of the last look that was logged, so an unchanged gap is logged once


def check():
    """One look: 1 eth_call when no direction shows a gain above MIN_INTEREST. Returns True when one did."""
    pairs = [(m, s) for m in (False, True) for s in SCREEN_SIZES]
    gains = quotes(pairs)
    seen = False
    for mint in (False, True):
        mine = tuple(g for (m, _), g in zip(pairs, gains) if m == mint)
        if max(mine) < MIN_INTEREST:
            if max(mine) > 0 and _last.get(mint) != mine:
                _last[mint] = mine
                log('check', result='below_interest', mint=mint, screen_gains_usdc=list(mine))
            continue
        if MODE == 'paper' and _last.get(mint) == mine:
            continue                                                  # paper sends nothing: the same gap is logged once
        seen = True
        amount, gross = best_size(mint)
        if gross < MIN_INTEREST:
            continue
        base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
        try:
            estimate = int(rpc('eth_estimateGas', call_params(run_calldata(mint, amount, 1))), 16)
        except Exception as e:
            log('simulate_revert', step='estimate', mint=mint, gross_usdc=gross, error=str(e)[:200])
            continue
        gas_limit = estimate * 21 // 20                               # the estimate (2.6-2.8M) already sits 25 pct above the gas used (2.0-2.2M)
        gross_wei = int(gross / 1e6 / ETH_REF_USD * 1e18)             # gross in wei at the reference price (a low value)
        tip = min(TIP_MAX_WEI, gross_wei // TIP_SHARE_DEN // gas_limit)
        max_fee = base_fee + base_fee // 4 + tip
        cap = gas_limit * max_fee + L1_FEE_ALLOW_WEI                  # the most this send should cost
        cap_usd = cap / 1e18 * ETH_REF_USD
        cap_usdc = int(cap_usd * 1e6) + 1                             # the same in USDC units = the tx's minProfit
        log('opportunity', mint=mint, amount_usdc=amount, gross_usdc=gross, screen_gains_usdc=list(mine), cap_usdc=cap_usdc,
            base_fee=base_fee, tip_wei=tip, max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit, cap_usd=round(cap_usd, 4))
        if max_fee > MAX_FEE_CAP_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
            log('opportunity_skip', reason='fee_gas_or_usd_cap', max_fee_wei=max_fee, gas_limit=gas_limit, cap_usd=cap_usd)
            continue
        if gross * SEND_MULT_DEN <= cap_usdc * SEND_MULT_NUM:         # send only when expected gross > 1.3 x this send's gas cap
            log('opportunity_skip', reason='gross_below_send_line', gross_usdc=gross, cap_usdc=cap_usdc)
            _last[mint] = mine
            continue
        checked, err = gain_of(mint, amount, cap_usdc, gas_limit)     # the exact call that would be signed (minProfit = gas cap)
        if checked <= cap_usdc:
            log('simulate_revert', step='guard', mint=mint, gross_usdc=gross, cap_usdc=cap_usdc, error=err)
            continue
        if MODE == 'paper':
            _last[mint] = mine
            log('paper_sim', result='success', mint=mint, amount_usdc=amount, gross_usdc=checked,
                cap_usdc=cap_usdc, gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
        else:
            send_live(mint, amount, checked, cap_usdc, max_fee, tip, gas_limit)
            break                                                     # prices moved: read again before the other direction
    return seen


def main():
    """Timer loop. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), wblt=WBLT, router=ROUTER, poll_seconds=POLL)
    next_poll = 0
    looks = 0
    while True:
        try:
            now = time.time()
            if now >= next_poll:
                next_poll = now + POLL
                seen = check()
                looks += 1
                if looks % 100 == 1 and not seen:
                    log('heartbeat', looks=looks)
                if seen and MODE == 'live':
                    next_poll = time.time() + 6    # part of the gap may be left, or the send lost: look again soon
            else:
                time.sleep(max(0.5, min(30, next_poll - now)))
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            time.sleep(86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 5)   # to 00:00 UTC
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            next_poll = time.time() + POLL
            time.sleep(5)


if __name__ == '__main__':
    main()
