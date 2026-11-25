"""trial-folio-nav-bsc: Reserve Folio (index token) redeem round trip on BSC, one atomic executor call.

A Folio share (CMC20, "CoinMarketCap 20 Index DTF") is redeemed for its basket of 16 tokens by anyone with
Folio.redeem(). When CMC20 is cheap in one of its PancakeSwap V3 pools (CMC20/WBNB, CMC20/USDT) relative to the basket,
this round trip pays: flash-swap CMC20 out of the pool, redeem it, sell the basket for WBNB, pay the pool what the swap
owes, keep the rest. Executor 0x742414b7 and three smaller operators take it about 20 times a day in this direction
(README). The bot simulates the executor's probe() on a timer, sweeps the size when a route shows a gain and, when the
simulated gain exceeds the signed gas cap, sends it (BOT_MODE=live) or logs a paper simulation (BOT_MODE=paper). The
executor reverts unless its WBNB balance grows by minProfit after the pool is paid, so a lost attempt costs gas only.
"""
import datetime
import json
import os
import sys
import time
from pathlib import Path
import urllib.request

sys.path.append('/opt/farm/lib')   # farmbot_signer lives here; the live service does not add it

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'bsc'

# Addresses: read from the incumbent's takes (0x39a048d7..., 0xf45b051f...) and checked with token0()/token1()/fee()/
# factory()/symbol() getters (scratch/trial-folio-nav-bsc/pools.py, pools.json), see README.
WBNB = '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'
USDT = '0x55d398326f99059ff775485246999027b3197955'
CMC20 = '0x2f8a339b5889ffac4c5a956787cda593b3c36867'      # Reserve Folio "CoinMarketCap 20 Index DTF", version 5.0.0
BTCB = '0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c'
ETH = '0x2170ed0880ac9a755fd29b2688956bd959f933f8'
XRP = '0x1d2f0da169ceb9fc7b3144628db156f3f6c60dbe'
SOL = '0x570a5d26f7765ecb712c0924e4de545b89fd43df'
TRX = '0xce7de646e7208a4ef112cb6ed5038fa6cc6b12e3'
DOGE = '0xba2ae424d960c26247dd6c32edc70b295c744c43'
ADA = '0x3ee2200efb3400fabb9aacf31297cbdd1d435d47'
HYPE = '0xaed86a53a8f3dbba4fb6ae7a5f65f337c606bf28'
LINK = '0xf8a0bf9cf54bb92f17374d9e9a321e6a111a51bd'
XLM = '0x43c934a845205f0b514417d757d7235b8f53f1b9'
BCH = '0x8ff795a6f4d97e7887c79bea79aba5cc76444adf'
UNI = '0xbf5140a22578168fd562dccf235e5d43a02ce9b1'
AVAX = '0x1ce0c2827e2ef14d5c4f29a091d735a204794041'
ZEC = '0x1ba42e5193dfa8b03d15dd1b86a3113bbbef8eeb'
LTC = '0x4338665cbb7b2485a8855a139b75d5e34ab0db94'
CMC20_WBNB = '0x4353e8c1cfde30dd87f1ed971d27c8f68439bd61'   # PancakeSwap V3 CMC20/WBNB 0.05 pct
CMC20_USDT = '0xb4bd7ec1df39806df478d0ce540580a118671eea'   # PancakeSwap V3 CMC20/USDT 0.05 pct
P_USDT_WBNB_UNI = '0x47a90a2d92a8367a91efa1906bfc8c1e05bf10c4'   # Uniswap V3 USDT/WBNB 0.01 pct
P_USDT_WBNB_PCS = '0x172fcd41e0913e95784454622d1c3724f546f849'   # PancakeSwap V3 USDT/WBNB 0.01 pct (token0 USDT)
Z = '0x0000000000000000000000000000000000000000'
# Step = (kind, target, tokenIn, param): 0 V3-style swap of the whole balance of tokenIn, 1 Folio redeem of the whole
# share balance, 2 V2 pair swap of the whole balance (param = fee numerator per 10000), 3 V3-style exact-output buy of
# what is still owed to the outer pool, paid in tokenIn.
BASKET = [
    (1, CMC20, Z, 0),
    (0, '0x62edaf2a56c9fb55be5f9b1399ac067f6a37013b', BTCB, 0),    # PancakeSwap V3 BTCB/WBNB 0.01 pct
    (0, '0x62fcb3c1794fb95bd8b1a97f6ad5d8a7e4943a1e', ETH, 0),     # PancakeSwap V3 ETH/WBNB 0.01 pct
    (0, '0x5a35bdce7791023b74aeb595f5511341972698a0', XRP, 0),     # XRP/USDT, factory 0x73dc984d (dynamic-fee V3 fork)
    (0, '0xfd8d957404aedc1a382d968e016cb8c313f2725c', SOL, 0),     # SOL/WBNB, factory 0x73dc984d
    (0, '0xf683113764e4499c473acd38fc4b37e71554e4ad', TRX, 0),     # PancakeSwap V3 WBNB/TRX 0.25 pct
    (2, '0x1ef315fa08e0e1b116d97e3dfe0af292ed8b7f02', DOGE, 9980), # Biswap DOGE/WBNB (factory 0x858e3312, swapFee() = 2 per 1000)
    (2, '0x8860922eb2795ab0d57363653dd7ebf18d7c0a42', ADA, 9980),  # Biswap ADA/WBNB (swapFee() = 2)
    (0, '0x514757b693445372705a015b5fbda45b251c11d5', HYPE, 0),    # PancakeSwap V3 HYPE/WBNB 0.05 pct
    (2, '0xaebe45e3a03b734c68e5557ae04bfc76917b4686', LINK, 9980), # PancakeSwap V1 WBNB/LINK (factory 0xbcfccbde, 0.2 pct)
    (2, '0xeeb72afcf53a846c0549084ba7450edca2014189', XLM, 9975),  # PancakeSwap V2 XLM/WBNB (factory 0xca143ce3, 0.25 pct)
    (0, '0x14cfad9a4fcb5fb4f702f5d0e90dcc633e1ded9a', BCH, 0),     # PancakeSwap V3 BCH/WBNB 0.25 pct
    (0, '0x554548b404213c7efcdbab933f52edfe3c581834', UNI, 0),     # Uniswap V3 WBNB/UNI 1 pct
    (2, '0x151268db1579ebc5306d4aaa5dcc627646e6986f', AVAX, 9975), # PancakeSwap V2 AVAX/WBNB
    (0, '0x6701b287c8170d6c290c6f4ef426782bd61ae310', ZEC, 0),     # PancakeSwap V3 ZEC/USDT 0.05 pct
    (0, '0xce09e903442eabb48c525aa29c9c4238f146a6df', LTC, 0),     # PancakeSwap V3 LTC/WBNB 0.05 pct
]
ROUTES = {
    # buy CMC20 with WBNB (flash swap), redeem, sell the basket to WBNB (XRP and ZEC through USDT), pay the pool
    'redeem_wbnb': {'outer': CMC20_WBNB, 'pay': WBNB, 'steps': BASKET + [(0, P_USDT_WBNB_UNI, USDT, 0)],
                    'probe': 7 * 10**17, 'sizes': [3 * 10**17, 7 * 10**17, 15 * 10**17, 25 * 10**17]},
    # buy CMC20 with USDT (flash swap), redeem, sell the basket, buy the missing USDT with WBNB, pay the pool
    'redeem_usdt': {'outer': CMC20_USDT, 'pay': USDT, 'steps': BASKET + [(3, P_USDT_WBNB_PCS, WBNB, 0)],
                    'probe': 400 * 10**18, 'sizes': [170 * 10**18, 400 * 10**18, 850 * 10**18, 1700 * 10**18]},
}
SWAP_TOPIC = '0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83'   # PancakeSwap V3 Swap (cast keccak)
SEL_RUN = '0xc60ac4e9'    # cast sig run(address,address,address,uint256,(uint8,address,address,uint256)[],uint256)
SEL_PROBE = '0xb98916e9'  # cast sig probe(address,(address,address,uint256,(uint8,address,address,uint256)[])[])
SEL_SLOT0 = '0x3850c7bd'  # cast sig slot0()
PROBE_GAS = 60_000_000    # eth_call only: one reverted trial of about 2.4m gas per route

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_BSC') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BSC or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

# ---- loss guard -----------------------------------------------------------------------------
# BSC has no base fee and no L1 fee: the worst case of one send is gasLimit x gasPrice, both signed.
MAX_TX_USD = 0.90              # gasLimit x gasPrice at the pool's BNB/USD x PRICE_MARGIN stays under this
PRICE_MARGIN = 1.15            # the cap is checked at a BNB price 15 pct above the pool's
BNB_USD_MIN, BNB_USD_MAX = 100.0, 5000.0   # a pool price outside this band is treated as unreadable: no send
MAX_FEE_WEI = 1_000_000_000    # 1 gwei absolute ceiling for the gas price (the chain's price is 0.05 gwei)
MAX_GAS_LIMIT = 3_700_000      # fork: 2.03m-2.20m used, estimates 2.51m-2.68m; incumbents 1.85m-2.8m
SIM_GAS = 3_700_000
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 12, 10    # gas limit = eth_estimateGas x 1.20 + GAS_EXTRA
GAS_EXTRA = 100_000            # the redeem and 17 swaps cross more or fewer ticks than at estimate time
# BSC orders a block by gas price; the incumbents pay the 0.05 gwei floor (max seen 0.0501).
# The bot bids at most BID_SHARE_PCT of the simulated gross, spread over the gas limit, on top of eth_gasPrice.
BID_SHARE_PCT = 20
ROUGH_GAS = 2_500_000          # only for the cheap pre-filter before an estimate is made
POLL_INTERVAL = 40             # timer: one probe() eth_call (26 CU) every 40 s = 2,160 x 26 = 56,160 CU/day.
                               # No feed filter: the two CMC20 pools emit about 1,600 and 3,500 Swap logs a day, which is
                               # a busy event by the feed rules (wiki infra/feed.md), and basket-side moves have no event.
BURST_INTERVAL = 5             # after a probe shows any gain (a gap is building): look every 5 s ...
BURST_SECONDS = 60             # ... for 60 s (12 probes) ...
BURST_REARM = 1200             # ... at most once per 20 min: 72 bursts x 12 x 26 = 22,464 CU/day at most
BLOCK = 'latest'               # selftest.py replays check() at a past block by setting this
SEND_COOLDOWN = 20             # per route
RELAY_CU_CAP = 95_000          # per UTC day
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 20, 'eth_getBalance': 20}
_id = 0


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': round(time.time(), 3), 'ev': ev, **kw}
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
    if budget['cu'] + cost > RELAY_CU_CAP:
        raise ReadBudgetExceeded(f'{RELAY_CU_CAP} relay CU/day bot cap reached')
    budget['cu'] += cost
    CU_FILE.write_text(json.dumps(budget))
    _id += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:300]}')
    return ans['result']


def word(n):
    return format(n, '064x')


def aword(a):
    return a.lower().removeprefix('0x').zfill(64)


def bot_address():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a.get('address') if isinstance(a, dict) else a   # my_address() returns {"ok":..., "address":...}
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def steps_words(steps):
    """A Step[] body: length, then each static 4-word tuple (kind, target, tokenIn, param)."""
    return word(len(steps)) + ''.join(word(k) + aword(t) + aword(i) + word(p) for k, t, i, p in steps)


def calldata(route, amount, min_profit):
    """ABI encoding of run(outerPool, payToken, wnative, amountIn, Step[], minProfit) (checked against cast in selftest.py)."""
    r = ROUTES[route]
    return (SEL_RUN + aword(r['outer']) + aword(r['pay']) + aword(WBNB) + word(amount) + word(6 * 32) + word(min_profit)
            + steps_words(r['steps']))


def probe_calldata():
    """ABI encoding of probe(wnative, Route[]) over every route at its probe size (checked against cast in selftest.py).
    Route = (outerPool, payToken, amountIn, Step[]) is a dynamic tuple: the array body is offsets, then the tuples."""
    inner = [aword(r['outer']) + aword(r['pay']) + word(r['probe']) + word(4 * 32) + steps_words(r['steps'])
             for r in ROUTES.values()]
    offsets, pos = [], len(inner) * 32
    for x in inner:
        offsets.append(word(pos))
        pos += len(x) // 2
    return SEL_PROBE + aword(WBNB) + word(2 * 32) + word(len(inner)) + ''.join(offsets) + ''.join(inner)


def probe_all(ctx):
    """One eth_call: the executor tries every route at its probe size and reverts each trial. {route: gain or None}."""
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': probe_calldata(), 'gas': hex(PROBE_GAS)}, BLOCK]
    raw = rpc('eth_call', params + ([ov] if ov else []))[2:]
    n = int(raw[64:128], 16)
    if n != len(ROUTES):
        raise RuntimeError(f'probe returned {n} gains for {len(ROUTES)} routes')
    gains = [int(raw[128 + 64 * i: 192 + 64 * i], 16) for i in range(n)]
    return {route: (g or None) for route, g in zip(ROUTES, gains)}


def sim(data, ctx, gas=SIM_GAS):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(gas)}, BLOCK] + ([ov] if ov else [])
    return int(rpc('eth_call', params)[2:66], 16)


def try_sim(data, ctx, gas=SIM_GAS):
    try:
        return sim(data, ctx, gas)
    except ReadBudgetExceeded:
        raise
    except RuntimeError:
        return None    # executor revert: the round trip does not pay


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, BLOCK] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def bnb_usd():
    """USDT per WBNB from slot0 of the PancakeSwap V3 USDT/WBNB 0.01 pct pool (token0 USDT, token1 WBNB, both 18 dec)."""
    raw = rpc('eth_call', [{'to': P_USDT_WBNB_PCS, 'data': SEL_SLOT0}, BLOCK])
    sqrt_p = int(raw[2:66], 16)
    if sqrt_p == 0:
        raise RuntimeError('BNB/USD pool unreadable')
    price = 2**192 / (sqrt_p * sqrt_p)       # token1 per token0 = WBNB per USDT, inverted
    if not BNB_USD_MIN < price < BNB_USD_MAX:
        raise RuntimeError(f'BNB/USD {price} outside the plausible band')
    return price


def winner_block(send_block, our_hash):
    """Block and tx of the last swap on either CMC20 pool up to our block (ours if we won): every route swaps there."""
    logs = rpc('eth_getLogs', [{'address': [CMC20_WBNB, CMC20_USDT], 'fromBlock': hex(max(0, send_block - 400)),
                                'toBlock': hex(send_block), 'topics': [SWAP_TOPIC]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    last = max(logs, key=lambda x: (int(x['blockNumber'], 16), int(x['logIndex'], 16)))
    return int(last['blockNumber'], 16), last['transactionHash']


def send_live(route, data, gas_limit, gas_price, gross, min_profit, cap_wei, amount):
    import farmbot_signer
    # BSC has no base fee: maxFeePerGas = maxPriorityFeePerGas = the gas price the bot bids
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, gas_price, max_priority_fee_per_gas=gas_price)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply, route=route, amount=amount)   # final, never retried
        return
    log('send', hash=h, route=route, amount=amount, gas_limit=gas_limit, max_fee=gas_price, priority=gas_price,
        gross_wei=gross, min_profit_wei=min_profit, gas_cap_wei=cap_wei, executor=EXEC)
    receipt = None
    for _ in range(30):
        time.sleep(1)
        try:
            receipt = rpc('eth_getTransactionReceipt', [h])
        except ReadBudgetExceeded:
            break
        except Exception:
            receipt = None
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, route=route, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        wb, wtx = winner_block(b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, route=route, result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        send_block=b, winner_block=wb, winner_tx=wtx, blocks_after_winner=(b - wb if wb is not None else None),
        expected_gross_wei=gross, net_wei=(gross - cost if status else -cost), amount=amount)


def take(s, route, probe, ctx, now):
    """A route shows a gain at the probe size: sweep, cap, guard, then send or paper-log."""
    chain_price = int(rpc('eth_gasPrice', []), 16)
    if probe <= ROUGH_GAS * chain_price * 8 // 10:
        log('check', route=route, probe_gain_wei=probe, chain_gas_price=chain_price, reason='gain_below_gas')
        return False
    r = ROUTES[route]
    rows = {r['probe']: probe}
    for size in r['sizes']:
        if size != r['probe']:
            rows[size] = try_sim(calldata(route, size, 1), ctx)
    amount, gross = max(((k, v) for k, v in rows.items() if v), key=lambda x: x[1])
    try:
        est = estimate(calldata(route, amount, 1), ctx)
    except RuntimeError as e:
        log('opportunity_skip', route=route, reason='estimate_revert', error=str(e)[:160], amount=amount, gross_wei=gross)
        return False
    gas_limit = est * GAS_MARGIN_NUM // GAS_MARGIN_DEN + GAS_EXTRA
    try:
        price = bnb_usd()
    except RuntimeError as e:
        log('opportunity_skip', route=route, reason='bnb_usd_unreadable', error=str(e)[:160])
        return False
    bid = gross * BID_SHARE_PCT // 100 // gas_limit                      # bid: at most 20 pct of gross over the gas limit
    usd_ceiling = int(MAX_TX_USD / (price * PRICE_MARGIN) * 1e18 / gas_limit) - 1
    gas_price = min(chain_price + bid, MAX_FEE_WEI, usd_ceiling)
    cap_wei = gas_limit * gas_price                                      # the signed worst case of one send
    cap_usd = cap_wei / 1e18 * price
    min_profit = cap_wei + 1                                             # a win always pays more than the signed gas cap
    log('opportunity', route=route, sweep=rows, amount=amount, gross_wei=gross, chain_gas_price=chain_price,
        gas_estimate=est, gas_limit=gas_limit, gas_price=gas_price, gas_cap_wei=cap_wei, gas_cap_usd=cap_usd,
        bnb_usd=price, min_profit_wei=min_profit)
    if gas_price < chain_price or gas_limit > MAX_GAS_LIMIT or cap_usd * PRICE_MARGIN >= MAX_TX_USD:
        log('opportunity_skip', route=route, reason='fee_gas_or_usd_cap', gas_price=gas_price, chain_gas_price=chain_price,
            gas_limit=gas_limit, gas_cap_usd=cap_usd)
        return False
    if gross <= cap_wei:
        log('opportunity_skip', route=route, reason='gross_below_gas_cap', gross_wei=gross, gas_cap_wei=cap_wei)
        return False
    if s.setdefault('cooldown', {}).get(route, 0) > now:
        log('opportunity_skip', route=route, reason='cooldown')
        return False
    data = calldata(route, amount, min_profit)
    checked = try_sim(data, ctx, gas_limit)      # the exact guarded call at the signed gas limit
    if not checked:
        log('simulate_revert', route=route, amount=amount, min_profit_wei=min_profit, gas_limit=gas_limit)
        return False
    s['cooldown'][route] = now + SEND_COOLDOWN
    if MODE == 'live':
        balance = int(rpc('eth_getBalance', [ctx[0], 'latest']), 16)
        if balance < cap_wei:
            log('opportunity_skip', route=route, reason='wallet_below_gas_cap', wallet_wei=balance, gas_cap_wei=cap_wei)
            return False
        send_live(route, data, gas_limit, gas_price, checked, min_profit, cap_wei, amount)
    else:
        log('paper_sim', result='success', route=route, amount=amount, gross_wei=checked, min_profit_wei=min_profit,
            gas_limit=gas_limit, gas_price=gas_price, gas_cap_wei=cap_wei, net_wei_at_cap=checked - cap_wei,
            bnb_usd=price, gas_cap_usd=cap_usd)
    return True


def check(s):
    """One look at the chain: probe every route, act on those that show a gain."""
    now = time.time()
    s['last_check'] = now
    ctx = exec_ctx()
    probes = probe_all(ctx)
    live = {r: g for r, g in probes.items() if g}
    if not live:
        log('check', probes=probes, reason='nothing_to_take')
        return
    if now >= s.get('burst_rearm', 0):
        s['burst_until'] = now + BURST_SECONDS
        s['burst_rearm'] = now + BURST_REARM
        log('burst', seconds=BURST_SECONDS, interval=BURST_INTERVAL, probes=probes)
    for route, gain in sorted(live.items(), key=lambda x: -x[1]):
        if take(s, route, gain, ctx, now):
            break    # one send per look


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {'last_check': 0, 'cooldown': {}}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def main():
    s = load_state()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), routes=list(ROUTES), poll_seconds=POLL_INTERVAL)
    while True:
        try:   # every RPC read of the bot happens inside this try (ReadBudgetExceeded sleeps to 00:00 UTC)
            interval = BURST_INTERVAL if time.time() < s.get('burst_until', 0) else POLL_INTERVAL
            wait = interval - (time.time() - s.get('last_check', 0))
            if wait > 0:
                time.sleep(min(wait, interval))
                continue
            check(s)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            tomorrow = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
            time.sleep(max(60, (tomorrow - datetime.datetime.now(datetime.timezone.utc)).total_seconds()))
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            s['last_check'] = time.time()
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
