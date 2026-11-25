#!/usr/bin/env python3
"""Trial: feUSD discount -> Felix redemption round trip on HyperEVM through the FeusdRedeemTake executor.

When feUSD trades below its redemption value in the HyperSwap V3 feUSD/USDT0 pool, one transaction
flash-borrows USDT0 from Morpho Blue, buys feUSD, redeems it at Felix's CollateralRegistry
(permissionless redeemCollateral) for WHYPE + kHYPE, sells kHYPE to WHYPE, sells just enough WHYPE to
repay the loan, unwraps the rest and pays it to the bot wallet as native HYPE. The executor reverts
unless the wallet receives at least minProfit, so a lost attempt costs gas only.

The bot waits on the feed for the pool's Swap event (price is in the event), keeps a 10 min safety
poll of slot0, and simulates through the relay before every send.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546').rstrip('/')
CHAIN = 'hyperevm'

# Route (all call arguments of the executor; verified by getters and the incumbent's trace
# 0x30ba123ac9bbee2a970571688eb0805777455b5e23f528aec3241c91a8eb9613)
MORPHO = '0x68e37de8d93d3496ae143f2e900490f6280c57cd'
USDT0 = '0xb8ce59fc3717ada4c02eadf9682a9e934f625ebb'
FEUSD = '0x02c6a2fa58cc01a18b8d9e00ea48d65e4df26c70'
WHYPE = '0x5555555555555555555555555555555555555555'
KHYPE = '0xfd739d4e423301ce9385c1fb8850539d657c296d'
REGISTRY = '0x9de1e57049c475736289cb006212f3e1dce4711b'      # Felix CollateralRegistry
ROUTER = '0x1ebdfc75ffe3ba3de61e7138a3e8706ac841af9b'        # HyperSwap V3 SwapRouter
ROUTER_LST = '0x4e2960a8cd19b467b82d26d83facb0fae26b094d'    # router the incumbent uses for kHYPE
POOL = '0x44a59f7859f199768e585133e0a5ab2da1350600'          # feUSD/USDT0 0.01%, token0 feUSD, token1 USDT0
POOL_WHYPE = '0xbd19e19e4b70eb7f248695a42208bc1edbbfb57d'    # WHYPE/USDT0 0.05%, token0 WHYPE, token1 USDT0
T_SWAP = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'  # cast keccak Swap(address,address,int256,int256,uint160,uint128,int24)
SEL_TAKE = '0x11885c37'      # cast sig take((address x9, bytes x3, uint256 x6))
SEL_SLOT0 = '0x3850c7bd'

PAPER_EXEC = '0x8f7a45ebde059392e46a46dcc14ab24681a961ea'    # fork deployment; paper code override only
PAPER_OWNER = '0x1111111111111111111111111111111111111111'   # the owner baked into that deployment
EXEC = os.environ.get('EXECUTOR_ADDR_HYPEREVM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_HYPEREVM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

# ---- loss guard (trial rule: every send's gas limit x maxFeePerGas < 1 USD) ----
GAS_LIMIT = 1_950_000          # chain cap 2,000,000. fork: success 1,752,236 at 640 USDT0, lost attempt 1,856,971
MAX_FEE_WEI = 2 * 10**9        # hard ceiling on maxFeePerGas: 1.95M x 2 gwei = 0.0039 HYPE
SEND_CAP_USD = 0.95            # gas cap valued at the on-chain HYPE price x 1.15 must stay under this
HYPE_MARGIN = 1.15
BID_SHARE = 0.30               # priority fee bid is at most 30% of simulated gross
SIZES = [640, 320, 160, 80, 40]            # USDT0 flash sizes tried, largest first (incumbent uses 160)
MAX_FEE_PCT = 5 * 10**16       # Felix redemption fee ceiling argument (5%); profit check is the real guard
TRIGGER_PRICE = 0.9990         # feUSD/USDT0 pool price at or under which the route is simulated
                               # (selftest: +0.0029 HYPE at 0.99805 before incumbent block 51359838)
RESIM_DROP = 0.0005            # after a no-profit simulation: again only if the price fell this much more...
RESIM_AFTER_S = 600            # ...or after 10 min
SAFETY_POLL_S = 600
FEED_TIMEOUT_S = 55
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10,
           'eth_gasPrice': 10}
CU_CAP = 90_000                # relay CU/day, hard cap in code (trial rule: <= 100,000 with the feed)
_id = 0


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': time.time(), 'ev': ev, **kw}
    with LOG.open('a') as f:
        f.write(json.dumps(row, separators=(',', ':'), default=str) + '\n')


def rpc(method, params):
    global _id
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(CU_FILE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    cost = CU_COST.get(method, 26)
    if budget['cu'] + cost > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} relay CU/day bot cap reached')
    budget['cu'] += cost
    CU_FILE.write_text(json.dumps(budget))
    _id += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {ans["error"]}')
    return ans['result']


def word(n):
    return format(n, '064x')


def aw(a):
    return a.lower().removeprefix('0x').zfill(64)


def enc_bytes(hexstr):
    size = len(hexstr) // 2
    return word(size) + hexstr.ljust(((size + 31) // 32) * 64, '0')


def v3path(*parts):
    return ''.join(p[2:].lower() if isinstance(p, str) else format(p, '06x') for p in parts)


BUY_PATH = v3path(USDT0, 100, FEUSD)        # exactInput USDT0 -> feUSD
LST_PATH = v3path(KHYPE, 100, WHYPE)        # exactInput kHYPE -> WHYPE
REPAY_PATH = v3path(USDT0, 500, WHYPE)      # exactOutput (reversed): WHYPE -> USDT0


def calldata(amount_in, min_profit, max_gas_price, deadline):
    """take(Route): one dynamic tuple. Head = 9 addresses, 3 bytes offsets, 6 uints (18 words)."""
    tails = [enc_bytes(BUY_PATH), enc_bytes(LST_PATH), enc_bytes(REPAY_PATH)]
    offs, acc = [], 18 * 32
    for t in tails:
        offs.append(acc)
        acc += len(t) // 2
    head = ''.join(aw(a) for a in (MORPHO, USDT0, FEUSD, WHYPE, KHYPE, REGISTRY, ROUTER, ROUTER_LST, ROUTER))
    head += ''.join(word(o) for o in offs)
    head += ''.join(word(x) for x in (amount_in, 0, MAX_FEE_PCT, min_profit, max_gas_price, deadline))
    return SEL_TAKE + word(32) + head + ''.join(tails)


def sqrt_to_price(sq):
    """token1 (USDT0, 6 dp) per token0 (18 dp)."""
    return (sq / 2**96) ** 2 * 1e12


def pool_price(pool=POOL, block='latest'):
    return sqrt_to_price(int(rpc('eth_call', [{'to': pool, 'data': SEL_SLOT0}, block])[2:66], 16))


def signer():
    sys.path.append('/opt/farm/lib')
    import farmbot_signer
    return farmbot_signer


def owner():
    a = signer().my_address()
    a = a['address'] if isinstance(a, dict) else a
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def sim(amount_in, min_profit, max_gas_price, deadline, from_addr, exec_addr, code, block='latest'):
    """eth_call of the exact take(); returns the native gain in wei the wallet would receive."""
    tx = {'from': from_addr, 'to': exec_addr, 'data': calldata(amount_in, min_profit, max_gas_price, deadline),
          'gas': hex(GAS_LIMIT)}
    params = [tx, block] + ([{exec_addr: {'code': code}}] if code else [])
    return int(rpc('eth_call', params)[2:66], 16)


def competitor_block(send_block, exec_addr):
    """Nearest block where someone else bought feUSD from the pool (amount0 < 0) around our send."""
    logs = rpc('eth_getLogs', [{'address': POOL, 'fromBlock': hex(max(0, send_block - 300)),
                               'toBlock': hex(send_block + 5), 'topics': [T_SWAP]}])
    best = None
    for x in logs:
        if '0x' + x['topics'][2][-40:].lower() == exec_addr.lower():
            continue
        if int(x['data'][2:66], 16) >> 255:         # amount0 negative: feUSD left the pool
            b = int(x['blockNumber'], 16)
            if best is None or abs(b - send_block) < abs(best - send_block):
                best = b
    return best


def send_live(data, max_fee, priority, gain, size):
    reply = signer().send(CHAIN, EXEC, data, 0, GAS_LIMIT, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', reply=reply)       # final: no retry
        return
    receipt = None
    for _ in range(25):
        time.sleep(1.0)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, result='unknown', gas_used=None, winner_block=None, size_usdt0=size)
        return
    b = int(receipt['blockNumber'], 16)
    used = int(receipt['gasUsed'], 16)
    status = int(receipt['status'], 16)
    try:
        other = competitor_block(b, EXEC)
    except Exception:
        other = None
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16), send_block=b, winner_block=other,
        blocks_after_winner=(b - other if other is not None else None), simulated_gain_wei=gain, size_usdt0=size)


def evaluate(s, price, why, block='latest'):
    """Simulate the sizes; send (live) or log (paper) the best one whose gross exceeds the gas cap."""
    now = time.time()
    last = s.get('last_noprofit')
    if last and price > last[0] - RESIM_DROP and now - last[1] < RESIM_AFTER_S:
        return None
    from_addr = owner() if MODE == 'live' else PAPER_OWNER
    exec_addr = EXEC if MODE == 'live' else PAPER_EXEC
    code = None if MODE == 'live' else RUNTIME
    deadline = int(now) + 120
    best = None
    errors = {}
    for size in SIZES:
        try:
            gain = sim(size * 10**6, 1, MAX_FEE_WEI, deadline, from_addr, exec_addr, code, block)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            errors[size] = str(e)[:120]
            continue
        if best is None or gain > best[1]:
            best = (size, gain)
    if best is None:
        s['last_noprofit'] = [price, now]
        log('simulate_revert', why=why, price=price, errors=errors)
        return None
    size, gain = best
    base_fee = int(rpc('eth_gasPrice', []), 16)
    hype_usd = pool_price(POOL_WHYPE, block) * HYPE_MARGIN
    priority = int(gain * BID_SHARE / GAS_LIMIT)
    max_fee = min(MAX_FEE_WEI, base_fee * 2 + priority)
    priority = min(priority, max_fee)
    gas_cap_wei = GAS_LIMIT * max_fee
    gas_cap_usd = gas_cap_wei / 1e18 * hype_usd
    gross_usd = gain / 1e18 * hype_usd
    if max_fee < base_fee or gas_cap_usd >= SEND_CAP_USD or gain <= gas_cap_wei:
        s['last_noprofit'] = [price, now]
        log('opportunity_skip', why=why, price=price, size_usdt0=size, gain_wei=gain, gross_usd=gross_usd,
            gas_cap_wei=gas_cap_wei, gas_cap_usd=gas_cap_usd, base_fee=base_fee, hype_usd=hype_usd,
            reason='base_fee_above_fee_cap' if max_fee < base_fee else
            ('gas_cap_over_usd_limit' if gas_cap_usd >= SEND_CAP_USD else 'gross_not_above_gas_cap'))
        return None
    data = calldata(size * 10**6, gas_cap_wei, max_fee, deadline)     # minProfit = this send's gas cap
    try:
        gain = sim(size * 10**6, gas_cap_wei, max_fee, deadline, from_addr, exec_addr, code, block)  # the exact bytes
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', why=why, price=price, size_usdt0=size, error=str(e)[:200])
        return None
    log('opportunity', why=why, price=price, size_usdt0=size, gain_wei=gain, gross_usd=gross_usd,
        gas_cap_wei=gas_cap_wei, gas_cap_usd=gas_cap_usd, max_fee=max_fee, priority=priority,
        hype_usd=hype_usd, errors=errors, mode=MODE)
    s.pop('last_noprofit', None)
    if MODE == 'live':
        send_live(data, max_fee, priority, gain, size)
    else:
        log('paper_sim', result='success', size_usdt0=size, gain_wei=gain, gross_usd=gross_usd)
    return gain


def feed_wait(cursor):
    """Long-poll the pool's Swap event. Returns (cursor, price or None, must_reread)."""
    q = {'address': POOL, 'topic0': T_SWAP, 'timeout': str(FEED_TIMEOUT_S)}
    if cursor:
        q['after'] = cursor
    try:
        with urllib.request.urlopen(f'{FEED}/logs/{CHAIN}?' + urllib.parse.urlencode(q), timeout=FEED_TIMEOUT_S + 15) as r:
            ans = json.load(r)
    except Exception as e:           # 429 / 503 / connection error: we may have missed something
        log('feed_error', error=str(e)[:160])
        time.sleep(20)
        return cursor, None, True
    cursor = ans.get('cursor', cursor)
    if ans.get('gap'):
        log('feed_gap')
        return cursor, None, True
    logs = ans.get('logs') or []
    if not logs:
        return cursor, None, False
    if any(x.get('removed') for x in logs):
        return cursor, None, True
    last = logs[-1]
    price = sqrt_to_price(int(last['data'][2 + 128:2 + 192], 16))
    log('swap', block=int(last['blockNumber'], 16), price=price, n=len(logs), block_ts=last.get('blockTimestamp'))
    return cursor, price, False


def main():
    try:
        s = json.loads(STATE.read_text())
    except Exception:
        s = {}
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, trigger_price=TRIGGER_PRICE,
        gas_limit=GAS_LIMIT, sizes=SIZES)
    cursor = None
    last_poll = 0.0
    while True:
        try:
            cursor, price, reread = feed_wait(cursor)
            why = 'feed'
            if reread or time.time() - last_poll >= SAFETY_POLL_S:
                price = pool_price()
                last_poll = time.time()
                why = 'reread' if reread else 'safety_poll'
                log('poll', why=why, price=price)
            if price is not None and price <= TRIGGER_PRICE:
                evaluate(s, price, why)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('relay_error', error=str(e)[:180])
            time.sleep(10)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(10)
        STATE.write_text(json.dumps(s))


if __name__ == '__main__':
    main()
