#!/usr/bin/env python3
"""One-shot: Bundles.fi v2 indexes on ethereum, public Index.rebalance() left untaken after the ETH / BTC fall.

An Index is a weighted pool (Balancer-style invariant) without a swap function of its own: anyone may call
rebalance(tokenOut, amountOut, tokenIn, to, data). The index approves amountOut of tokenOut to `to`, calls
to.execute(data), and then requires (a) the weighted invariant of the (tokenIn, tokenOut) pair not to fall and
(b) a fee in the protocol token BUN of value swapFee / (1000 + swapFee) of the tokenIn received. Whoever calls it
keeps the difference between the index's internal price and the market price. The index never reads an oracle,
so after a market move its internal price stays behind until somebody rebalances it.

The bot reads balances, weights and the fee of each index, market prices from three Uniswap V3 pools and the
BUN / WETH Uniswap V2 pair, sizes every (tokenIn, tokenOut) pair with the closed-form invariant, simulates the
exact run() calldata of the best one against head, and (live) sends it through the BundlesRebalancer executor:
pull tokenOut, buy tokenIn and BUN with part of it, pay the index, convert the rest to USDC, revert unless the
USDC left is at least minProfit, pay it to the bot wallet. No principal: the index hands over tokenOut first.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', '').rstrip('/')
CHAIN = 'ethereum'

# Addresses: indexes and BUN from the DefiLlama adapter projects/bundles (KB protocols:1432), routers / pair / pools
# from the incumbent's traced take 0x970eeb6a...9c5c and factory getters (scratch/oneshot-bundles-rebalance-ethereum).
INDEXES = {
    'CORE': '0xe202345c1a32a98f894f02d077af98108376ade3',   # BUN / WBTC / USDC / WETH
    'IDX2': '0xd19d6750760a8f41fc376c81526fcd8b38ab0d5a',   # BUN / WBTC / PAXG / wstETH / USDC
}
BUN = '0x695f775551fb0d28b64101c9507c06f334b4ba86'
USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
WETH = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
WBTC = '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599'
WSTETH = '0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0'
DEC = {USDC: 6, WETH: 18, WBTC: 8, WSTETH: 18, BUN: 18}
SYM = {USDC: 'USDC', WETH: 'WETH', WBTC: 'WBTC', WSTETH: 'wstETH', BUN: 'BUN'}
TRADED = (USDC, WETH, WBTC, WSTETH)                       # PAXG (fee-on-transfer switch) is left alone
V3_ROUTER = '0xe592427a0aece92de3edee1f18e0157c05861564'  # Uniswap V3 SwapRouter (exactInput / exactOutput with deadline)
BUN_PAIR = '0x25ad147ba3c1d19bd26c62178332d977bc6911e6'   # Uniswap V2 BUN / WETH pair (token0 BUN), 0.3% fee
# Uniswap V3 pools used for prices (slot0) and their fee tier; token0 / token1 order is read at startup
POOLS = {
    (USDC, WETH): ('0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640', 500),
    (WBTC, WETH): ('0x4585fe77225b41b697c938b018e2ac67ac5a20c0', 500),
    (WSTETH, WETH): ('0x109830a1aaad605bbf02a9dfa7b0b92ec2fb7daa', 100),
}

SEL = {  # all from `cast sig`
    'run': '0xf3b922ab',           # run(address,address,uint256,address,address,uint256,uint256,(uint8,address,address,uint256,uint256,uint256,address,bytes)[])
    'swapFee': '0x54cf2aeb',        # swapFee()
    'locked': '0xf464efed',        # isRebalancingLocked()
    'getBalance': '0xf8b2cb4f',     # getBalance(address)
    'getCurrentWeight': '0x54ef1aa4', # getCurrentWeight(address)
    'slot0': '0x3850c7bd',          # slot0()
    'token0': '0x0dfe1681',         # token0()
    'getReserves': '0x0902f1ac',    # getReserves()
    'balanceOf': '0x70a08231',      # balanceOf(address)
}
T_REBALANCED = '0x619b96ef'         # Rebalanced topic0 prefix (from the receipts of the index)

PAPER_EXEC = '0x8f7a45ebde059392e46a46dcc14ab24681a961ea'    # fork deployment; paper code override only
PAPER_OWNER = '0x1111111111111111111111111111111111111111'   # the owner baked into that deployment (immutable)
EXEC = os.environ.get('EXECUTOR_ADDR_ETHEREUM') or os.environ.get('EXECUTOR_ADDR')
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'

# ---- loss guard ----
MIN_NET_USD = 10.0             # send only if simulated USDC profit - this send's gas cap >= 10 USD
MIN_PROFIT_SHARE = 0.7         # executor minProfit = 70% of the simulated profit (and never under the gas cap)
GAS_LIMIT_MAX = 1_500_000
GAS_MARGIN = 1.3
MAX_FEE_WEI = 15 * 10**9       # never sign above 15 gwei: 1.5M gas x 15 gwei = 0.0225 ETH (about 36 USD at 1,616)
PRIORITY_WEI = 5 * 10**8       # 0.5 gwei tip to the builder (private route), not a bid for anybody's order
DEADLINE_BLOCKS = 3            # executor reverts after head + 3 (private-send rule)
MAX_WINS = 6                   # one-shot: the legs of the leftover, then idle
MAX_SENDS = 20                 # whatever the results
POLL_S = 600                   # 144 polls/day
IDLE_S = 3600
FRACTIONS = [0.002, 0.005, 0.01, 0.02, 0.03, 0.045, 0.06, 0.08, 0.10, 0.125, 0.15, 0.18, 0.21, 0.25, 0.30]
CU_COST = {'eth_call': 26, 'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10, 'eth_getBlockByNumber': 20,
           'eth_estimateGas': 26}
CU_CAP = 150_000               # relay CU/day, hard cap in code
_id = 0


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    LOG.parent.mkdir(exist_ok=True)
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
    CU_FILE.parent.mkdir(exist_ok=True)
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


def call(to, data, block='latest'):
    return rpc('eth_call', [{'to': to, 'data': data}, block])


def u(to, data, block='latest'):
    return int(call(to, data, block)[2:66], 16)


# ---------------------------------------------------------------- calldata

def enc_step(kind, target, token, amount, aux0, aux1, recipient, path):
    p = path.removeprefix('0x')
    n = len(p) // 2
    return (word(kind) + aw(target) + aw(token) + word(amount) + word(aux0) + word(aux1) + aw(recipient)
            + word(0x100) + word(n) + p.ljust(((n + 31) // 32) * 64, '0'))


def run_data(index, token_out, amount_out, token_in, profit_token, min_profit, deadline_block, steps):
    encs = [enc_step(*s) for s in steps]
    offs, pos = [], 32 * len(encs)
    for e in encs:
        offs.append(pos)
        pos += len(e) // 2
    arr = word(len(encs)) + ''.join(word(o) for o in offs) + ''.join(encs)
    return (SEL['run'] + aw(index) + aw(token_out) + word(amount_out) + aw(token_in) + aw(profit_token)
            + word(min_profit) + word(deadline_block) + word(0x100) + arr)


def hop_fee(a, b):
    return (POOLS.get((a, b)) or POOLS[(b, a)])[1]


def route(a, b):
    """Token list a -> b: direct if one side is WETH, otherwise through WETH."""
    return [a, b] if WETH in (a, b) else [a, WETH, b]


def v3_path(tokens):
    out = tokens[0].removeprefix('0x')
    for x, y in zip(tokens, tokens[1:]):
        out += format(hop_fee(x, y), '06x') + y.removeprefix('0x')
    return '0x' + out


ZERO = '0x' + '0' * 40


# ---------------------------------------------------------------- state and prices

def read_index(index, block='latest'):
    st = {'swapFee': u(index, SEL['swapFee'], block), 'locked': u(index, SEL['locked'], block), 'bal': {}, 'w': {}}
    for t in TRADED + (BUN,):
        w = u(index, SEL['getCurrentWeight'] + aw(t), block)
        if w:
            st['w'][t] = w
            st['bal'][t] = u(index, SEL['getBalance'] + aw(t), block)
    return st


_tok0 = {}


def read_prices(block='latest'):
    """USDC per whole token from Uniswap V3 slot0 (mid, no fee), and the BUN / WETH V2 reserves."""
    weth_per = {}
    for (a, b), (pool, _fee) in POOLS.items():
        if pool not in _tok0:
            _tok0[pool] = '0x' + call(pool, SEL['token0'])[-40:]
        sq = u(pool, SEL['slot0'], block)
        p10 = (sq / 2**96) ** 2                                 # token1 raw per token0 raw
        t0 = _tok0[pool]
        t1 = b if t0 == a else a
        whole = p10 * 10 ** DEC[t0] / 10 ** DEC[t1]             # whole token1 per whole token0
        other = a                                                # the non-WETH token of the pool
        weth_per[other] = whole if t1 == WETH else 1 / whole     # WETH per whole `other`
    usdc_per_weth = 1 / weth_per[USDC]
    px = {WETH: usdc_per_weth, USDC: 1.0, WBTC: weth_per[WBTC] * usdc_per_weth, WSTETH: weth_per[WSTETH] * usdc_per_weth}
    r = call(BUN_PAIR, SEL['getReserves'], block)[2:]
    return px, (int(r[0:64], 16), int(r[64:128], 16))            # (BUN reserve, WETH reserve)


def weth_for_bun(bun_out, res):
    """Uniswap V2 getAmountIn (0.3% fee): WETH in for an exact BUN out."""
    r_bun, r_weth = res
    if bun_out >= r_bun:
        return None
    return r_weth * bun_out * 1000 // ((r_bun - bun_out) * 997) + 1


# ---------------------------------------------------------------- sizing

def required_in(st, t_in, t_out, amount_out):
    """Smallest tokenIn the invariant accepts for amount_out, plus a small margin for the 64.64 fixed-point log."""
    b_in, b_out = st['bal'][t_in], st['bal'][t_out]
    ratio = (1 - amount_out / b_out) ** (-st['w'][t_out] / st['w'][t_in]) - 1
    return int(b_in * ratio * 1.00002) + 10


def fee_bun(st, t_in, d_in):
    """minFee of Index.rebalance (same integer formula), plus 0.02%."""
    f = st['swapFee']
    num = d_in * st['bal'][BUN] * st['w'][t_in] * f
    den = st['bal'][t_in] * st['w'][BUN] * (1000 + f)
    return (num // den) * 10002 // 10000 + 10


def model(st, px, res, t_in, t_out, amount_out):
    """Expected USDC profit of one candidate at mid prices less pool fees (a filter; the eth_call decides)."""
    d_in = required_in(st, t_in, t_out, amount_out)
    bun = fee_bun(st, t_in, d_in)
    w4b = weth_for_bun(bun, res)
    if w4b is None:
        return None
    usd_out = amount_out / 10 ** DEC[t_out] * px[t_out]
    usd_in = d_in / 10 ** DEC[t_in] * px[t_in]
    usd_bun = w4b / 1e18 * px[WETH]
    return {'d_in': d_in, 'bun': bun, 'weth_for_bun': w4b, 'usd_out': usd_out, 'usd_in': usd_in, 'usd_bun': usd_bun,
            'profit': usd_out * 0.998 - usd_in * 1.001 - usd_bun * 1.001}


def build_steps(index, t_in, t_out, amount_out, m):
    """Steps run inside the index callback, after the executor has pulled amount_out of t_out."""
    steps = []
    d_in, bun, w4b = m['d_in'], m['bun'], m['weth_for_bun']
    need_weth = w4b + (d_in if t_in == WETH else 0)
    if t_out != WETH:    # buy the WETH needed (BUN leg, and tokenIn if it is WETH) with exact output
        steps.append((0, V3_ROUTER, t_out, need_weth, amount_out, 0, ZERO, v3_path(list(reversed(route(t_out, WETH))))))
    steps.append((2, BUN_PAIR, WETH, w4b, bun, 0, index, '0x'))                 # WETH -> BUN, paid to the index
    if t_in == WETH:
        steps.append((3, ZERO, WETH, d_in, 0, 0, index, '0x'))                  # tokenIn to the index
    else:                # buy tokenIn with exact output, delivered to the index
        steps.append((0, V3_ROUTER, t_out, d_in, amount_out, 0, index, v3_path(list(reversed(route(t_out, t_in))))))
    if t_out != USDC:    # the rest of tokenOut becomes USDC
        steps.append((1, V3_ROUTER, t_out, 0, 0, 0, ZERO, v3_path(route(t_out, USDC))))
    return steps


def candidates(block='latest'):
    """Best modelled size of every ordered pair of every index, best first."""
    px, res = read_prices(block)
    out = []
    for name, index in INDEXES.items():
        st = read_index(index, block)
        if st['locked'] or BUN not in st['w']:
            continue
        toks = [t for t in TRADED if t in st['w'] and st['bal'].get(t)]
        for t_out in toks:
            for t_in in toks:
                if t_in == t_out:
                    continue
                best = None
                for fr in FRACTIONS:
                    amt = int(st['bal'][t_out] * fr)
                    m = model(st, px, res, t_in, t_out, amt)
                    if m and (best is None or m['profit'] > best[1]['profit']):
                        best = (amt, m, fr)
                if best and best[1]['profit'] > 0:
                    out.append({'index_name': name, 'index': index, 't_in': t_in, 't_out': t_out, 'amount_out': best[0],
                                'fraction': best[2], 'm': best[1], 'swapFee': st['swapFee']})
    out.sort(key=lambda c: -c['m']['profit'])
    return out, px


# ---------------------------------------------------------------- send

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


def ctx():
    """(from, executor, state override list) for this mode."""
    if MODE == 'live':
        return owner(), EXEC, []
    runtime = (HERE / 'executor-runtime.hex').read_text().strip()
    return PAPER_OWNER, PAPER_EXEC, [{PAPER_EXEC: {'code': runtime}}]


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {'wins': 0, 'sends': 0}


def save_state(st):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(st))


def send_live(c, data, gas_limit, max_fee, deadline, sim_profit, st):
    st['sends'] += 1
    save_state(st)
    reply = signer().send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=PRIORITY_WEI)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', reply=reply)       # final: no retry of this request
        return
    receipt = None
    while True:
        time.sleep(4)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt or int(rpc('eth_blockNumber', []), 16) > deadline + 1:
            break
    if not receipt:
        receipt = rpc('eth_getTransactionReceipt', [h])
    if not receipt:
        log('send_result', hash=h, result='private_not_included', deadline_block=deadline, index=c['index'],
            pair=SYM[c['t_in']] + '>' + SYM[c['t_out']], gas_used=None, winner_block=None)
        return
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    if status:
        st['wins'] += 1
        save_state(st)
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16), send_block=int(receipt['blockNumber'], 16),
        winner_block=None, simulated_profit_usdc=sim_profit / 1e6, index=c['index'], pair=SYM[c['t_in']] + '>' + SYM[c['t_out']])


def evaluate(c, px, st):
    """Simulate the exact bytes of the candidate; send (live) or log (paper) if profit - gas cap >= MIN_NET_USD."""
    frm, ex, ov = ctx()
    head = rpc('eth_getBlockByNumber', ['latest', False])
    base_fee = int(head['baseFeePerGas'], 16)
    deadline = int(head['number'], 16) + DEADLINE_BLOCKS
    steps = build_steps(c['index'], c['t_in'], c['t_out'], c['amount_out'], c['m'])
    args = (c['index'], c['t_out'], c['amount_out'], c['t_in'], USDC)
    tag = dict(index=c['index'], index_name=c['index_name'], pair=SYM[c['t_in']] + '>' + SYM[c['t_out']],
               amount_out=c['amount_out'], fraction=c['fraction'], model_profit_usd=round(c['m']['profit'], 2))
    try:
        res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': run_data(*args, 1, deadline, steps)}, 'latest'] + ov)
        profit = int(res[2:66], 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', error=str(e)[:220], **tag)
        return False
    max_fee = min(MAX_FEE_WEI, base_fee * 2 + PRIORITY_WEI)
    try:
        est = int(rpc('eth_estimateGas', [{'from': frm, 'to': ex, 'data': run_data(*args, 1, deadline, steps)}, 'latest'] + ov), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('opportunity_skip', reason='estimate_failed', error=str(e)[:160], **tag)
        return False
    gas_limit = min(GAS_LIMIT_MAX, int(est * GAS_MARGIN))
    gas_cap_usd = gas_limit * max_fee / 1e18 * px[WETH] * 1.1
    net = profit / 1e6 - gas_cap_usd
    if max_fee < base_fee + PRIORITY_WEI or net < MIN_NET_USD:
        log('opportunity_skip', reason='base_fee_above_cap' if max_fee < base_fee + PRIORITY_WEI else 'net_under_min',
            profit_usdc=profit / 1e6, gas_cap_usd=gas_cap_usd, base_fee=base_fee, **tag)
        return False
    min_profit = max(int(profit * MIN_PROFIT_SHARE), int(gas_cap_usd * 1e6) + 1)
    data = run_data(*args, min_profit, deadline, steps)
    log('opportunity', profit_usdc=profit / 1e6, min_profit_usdc=min_profit / 1e6, gas_cap_usd=gas_cap_usd, gas_est=est,
        gas_limit=gas_limit, max_fee=max_fee, base_fee=base_fee, deadline_block=deadline, eth_usd=px[WETH],
        d_in=c['m']['d_in'], bun_fee=c['m']['bun'], mode=MODE, **tag)
    if MODE == 'live':
        send_live(c, data, gas_limit, max_fee, deadline, profit, st)
    else:
        log('paper_sim', result='success', profit_usdc=profit / 1e6, gas_cap_usd=gas_cap_usd, **tag)
    return True


def main():
    if MODE == 'live' and not EXEC:
        raise SystemExit('EXECUTOR_ADDR_ETHEREUM or EXECUTOR_ADDR is required in live mode')
    if not RELAY:
        raise SystemExit('RPC_RELAY_URL is required')
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, poll_s=POLL_S, indexes=INDEXES, cu_cap=CU_CAP)
    n = 0
    while True:
        try:
            st = load_state()
            if st['wins'] >= MAX_WINS or st['sends'] >= MAX_SENDS:
                log('idle', reason='one-shot done', **st)
                time.sleep(IDLE_S)
                continue
            cands, px = candidates()
            n += 1
            top = cands[0] if cands else None
            log('poll', n=n, eth_usd=px[WETH], n_cands=len(cands),
                best=(None if not top else dict(index=top['index_name'], pair=SYM[top['t_in']] + '>' + SYM[top['t_out']],
                                                fraction=top['fraction'], model_profit_usd=round(top['m']['profit'], 2))))
            acted = False
            for c in cands[:3]:
                if c['m']['profit'] < MIN_NET_USD:
                    break
                if evaluate(c, px, st):
                    acted = True
                    break
            time.sleep(30 if (acted and MODE == 'live') else POLL_S)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            nxt = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
            time.sleep(max(60, (nxt - now).total_seconds()))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('relay_error', error=str(e)[:180])
            time.sleep(60)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(60)


if __name__ == '__main__':
    main()
