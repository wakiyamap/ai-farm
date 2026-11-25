#!/usr/bin/env python3
"""trial: kDIEM (the wrapped Venice DIEM that about 28 launchpad 'agent' tokens are quoted in) has two public doors
at the Buffer: redeemDiem(kdiemIn, to) pays DIEM at par less the door fee (1 pct) on the spot, mintKdiem(diemIn, to)
is the reverse. Every agent token T has a hookless Uniswap v4 T/kDIEM pool and a USDC/T pool. When a trade moves one
of the two, the round trip
  redeem: USDC -> T -> kDIEM (v4), redeemDiem, DIEM -> USDC (Uniswap V3 pool)
  mint:   USDC -> DIEM (V3 pool), mintKdiem, kDIEM -> T -> USDC (v4)
pays. One transaction through the DoorArb executor with a free Morpho flash loan of USDC; it reverts unless its USDC
balance grew by minProfit, and sends all USDC to the bot wallet. No principal.
Timer bot: ONE Multicall3 eth_call every POLL seconds (slot0 of every pool, the door fee, the Buffer's DIEM); the
exact run() is simulated only for a route whose marginal round trip is above MIN_EDGE after all fees."""
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

# Addresses: from the incumbents' receipts (tx 0xe5a7b31b6b5d..., 0x392a1a9e1e88...) and the verified Buffer source
# (diem(), kdiem() read on chain by the proof script); each answered a getter on 2026-11-21.
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
DIEM = '0xf4d97f2da56e8c3098f3a8d538db630a2606a024'
KDIEM = '0xf8b22f75b7ee248ff723650f43c98b253e7dfb60'
BUFFER = '0x7eaef27fae47fee4f9bbe42e8e6421da8a334387'      # the two doors (proxy; implementation Buffer.sol verified)
PM = '0x498581ff718922c3f8e6a244956af099b2652b2b'          # Uniswap v4 PoolManager (emitter of the Swap / Initialize logs)
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'      # Morpho Blue: flashLoan, no fee
V3POOLS = ['0xf69cd40bc4c661d0dbabb3d74b4f2a228ad63270', '0xbc3231036ee1eca03e5f67fecedc640d21610823']  # USDC / DIEM
MULTICALL3 = '0xca11bde05977b3631167028862be2a173976ca11'
ZERO = '0x' + '0' * 40

# Selectors and topics from `cast sig` / `cast keccak` (2026-11-21).
SEL_RUN = '0xd8bd23b2'      # run((address,address,address,address,address,address,address,address,uint24,int24,uint24,int24,bool,uint256,uint256))
SEL_EXTSLOAD = '0x1e2eaeaf' # PoolManager.extsload(bytes32)
SEL_SLOT0 = '0x3850c7bd'    # slot0()
SEL_FEE = '0xddca3f43'      # fee()
SEL_TOKEN0 = '0x0dfe1681'   # token0()
SEL_DOORFEE = '0xa0b6af07'  # Buffer.doorFeeBps()
SEL_BALANCE = '0xb69ef8a8'  # Buffer.balance()
SEL_AGG3 = '0x82ad56cb'     # aggregate3((address,bool,bytes)[])
TOPIC_REDEEMED = '0x2cad238c55114fcd24f1f5817e50342ca5c16c874f5d9bcf33cf92f786dfbcd1'  # DiemRedeemed(address,address,uint256,uint256)
TOPIC_MINTED = '0x164233aeab8dda043e9103548abe901bd09f41e50569e6646f03215a3d911c6f'    # KdiemMinted(address,address,uint256,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000d00a5'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'
ROUTES = json.loads((HERE / 'routes.json').read_text())   # v4 pools per agent token: ids, slot0 storage slots, fees

POLL = 30                          # seconds between looks (one eth_call each)
MIN_EDGE = 0.003                   # marginal round trip must pay 0.3 pct after every fee before anything is simulated
MAX_SIMS_PER_LOOK = 2              # routes simulated per look (the widest first)
SIZES = [20, 50, 100, 200, 400]    # USDC flash sizes tried, smallest first; stops when the gain stops growing
MIN_INTEREST = 30_000              # 0.03 USDC: smaller gains are not worth a send
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send when gross > 1.3 x the send's gas cap
TIP_SHARE_DEN = 10                 # priority fee: at most 1/10 of gross spread over the gas limit ...
TIP_MAX_WEI = 2 * 10**8            # ... and never above 0.2 gwei
MAX_FEE_CAP_WEI = 3 * 10**8        # never sign above 0.3 gwei
GAS_LIMIT_MAX = 1_200_000          # 1.2M x 0.3 gwei = 0.00036 ETH = 0.90 USD at the reference price
L1_FEE_ALLOW_WEI = 2 * 10**12      # allowance for the OP Stack L1 data fee (measured on the incumbents: under 1e-8 ETH)
ETH_REF_USD = 2500.0               # USD cap reference, well above the price (about 1,670 USD on 2026-11-21)
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


def agg3(calls, block='latest'):
    """aggregate3 with allowFailure = true; returns a list of (success, return bytes hex without 0x)."""
    items = []
    for target, data in calls:
        raw = data.removeprefix('0x')
        items.append(a(target) + w(1) + w(0x60) + w(len(raw) // 2) + raw + '00' * ((-(len(raw) // 2)) % 32))
    offs, pos = [], 32 * len(items)
    for it in items:
        offs.append(pos)
        pos += len(it) // 2
    data = SEL_AGG3 + w(32) + w(len(items)) + ''.join(w(o) for o in offs) + ''.join(items)
    res = rpc('eth_call', [{'to': MULTICALL3, 'data': data}, block]).removeprefix('0x')
    n = int(res[64:128], 16)
    base = 128
    out = []
    for i in range(n):
        off = int(res[base + 64 * i:base + 64 * (i + 1)], 16) * 2 + base
        ok = int(res[off:off + 64], 16) == 1
        ln = int(res[off + 128:off + 192], 16) * 2
        out.append((ok, res[off + 192:off + 192 + ln]))
    if len(out) != len(calls):
        raise RuntimeError('aggregate3: unexpected return length')
    return out


# every distinct v4 pool of the routes, by id
POOLS = {}
for _r in ROUTES:
    for _p in (_r['u'], _r['k']):
        if _p:
            POOLS[_p['id']] = _p
POOL_IDS = sorted(POOLS)
_v3static = {}   # V3 pool -> (USDC is token0, fee in ppm); refreshed by every look


def read_state(block='latest'):
    """One eth_call: door fee, the Buffer's DIEM, slot0 of every v4 pool (PoolManager.extsload) and slot0, token0()
    and fee() of the V3 pools."""
    need = list(V3POOLS)      # fee() of these pools moves (5,981 and 5,429 ppm seen on 0xf69cd40b): read every look
    calls = [(BUFFER, SEL_DOORFEE), (BUFFER, SEL_BALANCE)]
    calls += [(p, SEL_SLOT0) for p in V3POOLS]
    calls += [(PM, SEL_EXTSLOAD + POOLS[i]['slot'][2:]) for i in POOL_IDS]
    calls += [(p, SEL_TOKEN0) for p in need] + [(p, SEL_FEE) for p in need]
    out = agg3(calls, block)
    k = 2 + len(V3POOLS) + len(POOL_IDS)
    for i, p in enumerate(need):
        ok0, t0 = out[k + i]
        okf, fee = out[k + len(need) + i]
        if ok0 and okf and len(t0) >= 64 and len(fee) >= 64:
            _v3static[p] = ('0x' + t0[24:64] == USDC, int(fee[:64], 16))
    for ok, ret in out[:2]:
        if not ok or len(ret) < 64:
            raise RuntimeError('buffer getter failed')
    state = {'door_bps': int(out[0][1][:64], 16), 'buffer_diem': int(out[1][1][:64], 16), 'v3': {}, 'v4': {}}
    for p, (ok, ret) in zip(V3POOLS, out[2:2 + len(V3POOLS)]):
        if ok and len(ret) >= 64 and p in _v3static:
            state['v3'][p] = int(ret[:64], 16)
    for i, (ok, ret) in zip(POOL_IDS, out[2 + len(V3POOLS):k]):
        if ok and len(ret) >= 64:
            v = int(ret[:64], 16)
            sq = v & ((1 << 160) - 1)
            proto = (v >> 184) & 0xffffff
            lp = (v >> 208) & 0xffffff
            if sq:
                state['v4'][i] = (sq, lp + max(proto & 0xfff, proto >> 12))   # price, total fee in ppm (upper bound)
    return state


def _price(sq):
    return (sq / 2**96) ** 2      # raw token1 per raw token0


def _rate(pool, sq, token_in):
    """Marginal raw units of the other token per raw unit of token_in, before fees."""
    p = _price(sq)
    return p if token_in == pool['c0'] else 1 / p


def candidates(state):
    """Routes whose marginal round trip pays more than MIN_EDGE after pool fees and the door fee. Float screen only:
    the executor's eth_call decides. Returns a list of dicts sorted by edge, widest first."""
    door = 1 - state['door_bps'] / 10**4
    # best V3 pool per direction: USDC per raw DIEM when selling DIEM, raw DIEM per USDC when buying
    sell, buy = None, None
    for p, sq in state['v3'].items():
        usdc0, fee = _v3static[p]
        usdc_per_diem = (1 / _price(sq) if usdc0 else _price(sq)) * (1 - fee / 10**6)
        diem_per_usdc = (_price(sq) if usdc0 else 1 / _price(sq)) * (1 - fee / 10**6)
        if sell is None or usdc_per_diem > sell[1]:
            sell = (p, usdc_per_diem)
        if buy is None or diem_per_usdc > buy[1]:
            buy = (p, diem_per_usdc)
    if sell is None:
        return []
    found = []
    for r in ROUTES:
        k = state['v4'].get(r['k']['id'])
        u = state['v4'].get(r['u']['id']) if r['u'] else None
        if k is None or (r['u'] and u is None):
            continue
        mid = r['agent'] if r['u'] else USDC
        # redeem direction: USDC -> mid -> kDIEM
        fwd = _rate(r['k'], k[0], mid) * (1 - k[1] / 10**6)                  # kDIEM per mid
        back = _rate(r['k'], k[0], KDIEM) * (1 - k[1] / 10**6)               # mid per kDIEM
        if r['u']:
            fwd *= _rate(r['u'], u[0], USDC) * (1 - u[1] / 10**6)            # mid per USDC
            back *= _rate(r['u'], u[0], mid) * (1 - u[1] / 10**6)            # USDC per mid
        edge_redeem = fwd * door * sell[1] - 1
        edge_mint = buy[1] * door * back - 1
        for mint, edge, v3 in ((False, edge_redeem, sell[0]), (True, edge_mint, buy[0])):
            if MIN_EDGE < edge < 50:      # an edge of thousands of pct is an emptied pool at its price bound
                found.append({'route': r, 'mint': mint, 'edge': edge, 'v3': v3})
    found.sort(key=lambda c: -c['edge'])
    return found


def run_calldata(c, amount, min_profit):
    r = c['route']
    fee_u, ts_u = (r['u']['fee'], r['u']['ts']) if r['u'] else (0, 0)
    words = [a(MORPHO), a(PM), a(BUFFER), a(c['v3']), a(USDC), a(DIEM), a(KDIEM), a(r['agent']),
             w(fee_u), w(ts_u), w(r['k']['fee']), w(r['k']['ts']), w(1 if c['mint'] else 0), w(amount), w(min_profit)]
    return SEL_RUN + ''.join(words)


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


def call_params(data, gas_limit=None, block='latest'):
    ex = executor()
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': ex, 'data': data}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx, block]
    if MODE == 'paper':
        params.append({ex: {'code': RUNTIME_FILE.read_text().strip()}})
    return params


def gain_of(c, amount, min_profit, gas_limit=None, block='latest'):
    """Return value of the exact run() as an eth_call (USDC units gained); 0 when it reverts."""
    ans = rpc('eth_call', call_params(run_calldata(c, amount, min_profit), gas_limit, block), raw=True)
    if 'error' in ans or not ans.get('result') or ans['result'] == '0x':
        return 0, str(ans.get('error'))[:160]
    return int(ans['result'], 16), None


def best_size(c):
    """Try SIZES smallest first; stop when the gain stops growing. Returns (amount in USDC units, gain, error)."""
    best = (0, 0, None)
    for s in SIZES:
        gain, err = gain_of(c, s * 10**6, 1)
        if gain <= best[1]:
            if best[1] == 0:
                best = (0, 0, err)
            break
        best = (s * 10**6, gain, None)
    return best


def last_door_block(block):
    """Block of the newest door use at the Buffer near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': BUFFER, 'fromBlock': hex(block - 300), 'toBlock': hex(block + 10),
                               'topics': [[TOPIC_REDEEMED, TOPIC_MINTED]]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(c, amount, gross, cap_usdc, max_fee, tip, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, run_calldata(c, amount, cap_usdc), 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
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
    common = dict(hash=tx_hash, token=c['route']['sym'], mint=c['mint'], amount_usdc=amount, expected_gross_usdc=gross,
                  cap_usdc=cap_usdc, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee') or '0x0', 16)
    try:
        winner = block if status else last_door_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        gross_usdc=gross if status else 0, send_block=block, winner_block=winner,
        tx_index=int(receipt['transactionIndex'], 16), **common)


_dust = {}    # route key -> pool prices at the last look whose simulated gain was below MIN_INTEREST


def check():
    """One look: 1 eth_call when no route is above MIN_EDGE. Returns True when a gain above MIN_INTEREST was seen."""
    state = read_state()
    seen = False
    sims = 0
    for c in candidates(state):
        if sims >= MAX_SIMS_PER_LOOK:
            break
        r = c['route']
        key = (r['k']['id'], r['u']['id'] if r['u'] else None, c['mint'])
        prices = (state['v4'].get(r['k']['id']), state['v4'].get(r['u']['id']) if r['u'] else None, state['v3'].get(c['v3']))
        if _dust.get(key) in (prices, prices[:2]):
            continue          # same prices as the last look that was too small: no second call, no log line
        sims += 1
        amount, gross, err = best_size(c)
        if gross < MIN_INTEREST:
            # a route that reverts (a one-sided launch pool: CurrencyNotSettled) is remembered by its v4 prices alone,
            # so a move of the DIEM pool does not re-simulate every such route
            _dust[key] = prices[:2] if gross == 0 else prices
            log('check', result='below_interest', token=r['sym'], mint=c['mint'], edge=round(c['edge'], 5), chain_gain_usdc=gross, error=err)
            continue
        seen = True
        base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
        try:
            estimate = int(rpc('eth_estimateGas', call_params(run_calldata(c, amount, 1))), 16)
        except Exception as e:
            log('simulate_revert', step='estimate', token=r['sym'], gross_usdc=gross, error=str(e)[:200])
            continue
        gas_limit = estimate * 12 // 10
        gross_wei = int(gross / 1e6 / ETH_REF_USD * 1e18)             # gross in wei at the reference price (a low value)
        tip = min(TIP_MAX_WEI, gross_wei // TIP_SHARE_DEN // gas_limit)
        max_fee = base_fee + base_fee // 4 + tip
        cap = gas_limit * max_fee + L1_FEE_ALLOW_WEI                  # the most this send should cost
        cap_usd = cap / 1e18 * ETH_REF_USD
        cap_usdc = int(cap_usd * 1e6) + 1                             # the same in USDC units = the tx's minProfit
        log('opportunity', token=r['sym'], agent=r['agent'], mint=c['mint'], edge=round(c['edge'], 5), v3pool=c['v3'],
            amount_usdc=amount, gross_usdc=gross, cap_usdc=cap_usdc, base_fee=base_fee, tip_wei=tip, max_fee_wei=max_fee,
            gas_estimate=estimate, gas_limit=gas_limit, cap_usd=round(cap_usd, 4), door_bps=state['door_bps'],
            buffer_diem=state['buffer_diem'])
        if max_fee > MAX_FEE_CAP_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
            log('opportunity_skip', reason='fee_gas_or_usd_cap', max_fee_wei=max_fee, gas_limit=gas_limit, cap_usd=cap_usd)
            continue
        if gross * SEND_MULT_DEN <= cap_usdc * SEND_MULT_NUM:         # send only when expected gross > 1.3 x this send's gas cap
            log('opportunity_skip', reason='gross_below_send_line', gross_usdc=gross, cap_usdc=cap_usdc)
            continue
        checked, err = gain_of(c, amount, cap_usdc, gas_limit)        # the exact call that would be signed (minProfit = gas cap)
        if checked <= cap_usdc:
            log('simulate_revert', step='guard', token=r['sym'], gross_usdc=gross, cap_usdc=cap_usdc, error=err)
            continue
        if MODE == 'paper':
            _dust[key] = prices                                       # paper sends nothing: do not re-log the same gap
            log('paper_sim', result='success', token=r['sym'], mint=c['mint'], amount_usdc=amount, gross_usdc=checked,
                cap_usdc=cap_usdc, gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
        else:
            send_live(c, amount, checked, cap_usdc, max_fee, tip, gas_limit)
            break                                                     # prices moved: read again before the next route
    return seen


def main():
    """Timer loop. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), buffer=BUFFER, routes=len(ROUTES), v4_pools=len(POOL_IDS), poll_seconds=POLL)
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
