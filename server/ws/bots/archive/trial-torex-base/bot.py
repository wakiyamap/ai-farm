#!/usr/bin/env python3
"""trial: Torex (SuperBoring / Superfluid DCA) liquidity mover on Base.

A Torex hands its accumulated in super token to whoever calls moveLiquidity() and asks for
TWAP-since-last-move x fv/(fv+t) of the out super token back; the discount grows with time, so the first
mover whose costs are covered takes it. The bot simulates its executor on a timer and sends when the
simulated profit exceeds the send's whole gas cap.
"""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', '').rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'base'
OWNER_PAPER = '0x1111111111111111111111111111111111111111'
EXEC_PAPER = '0x0000000000000000000000000000000000070e01'
EXEC_LIVE = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
RUNTIME = HERE / 'executor-runtime.hex'

# Addresses: super tokens and Torexes from receipts of the incumbent's moves (tx 0x0a733e7a..., 0x2eb5c8db...)
# and Torex.getPairedTokens(); SwapRouter02 from the Swap logs' sender and Uniswap's Base deployment list.
WETH = '0x4200000000000000000000000000000000000006'
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
SUP = '0xa69f80524381275a7ffdb3ae01c54150644c8792'
ROUTER = '0x2626664c2603336e57b271c5c0b26f421741e481'
POOL_WETH_USDC = '0xb4cb800910b228ed3d0834cf79d697127bbb00e5'   # Uniswap V3 0.01 pct, token0 WETH
L1_ORACLE = '0x420000000000000000000000000000000000000f'       # OP Stack GasPriceOracle
F100, F3000 = '000064', '000bb8'


def path(*parts):
    return ''.join(p[2:].lower() if p.startswith('0x') else p for p in parts)


# name, torex, inKind, outKind, mode, path, profit token, poll seconds
ROUTES = [
    ('USDCx-ETHx', '0x269f9ef6868f70fb20ddf7cfdf69fe1dbfd307de', 1, 2, 0, path(USDC, F100, WETH), WETH, 120),
    ('SUP-ETHx', '0x3f9e46eb52c124067e6bee4913601419d4b1d4b9', 0, 2, 0, path(SUP, F3000, WETH), WETH, 120),
    ('USDCx-SUP', '0xc3b4f5177e3d706931789b159e1df433c20439f1', 1, 0, 1, path(SUP, F3000, WETH, F100, USDC), USDC, 120),
    ('ETHx-USDCx', '0x267264cfb67b015ea23c97c07d609fbfc06adc17', 2, 1, 0, path(WETH, F100, USDC), USDC, 300),
    ('SUP-USDCx', '0x91c673f8ab9dbfd95847f6c7e62fa4a72110337e', 0, 1, 0, path(SUP, F3000, WETH, F100, USDC), USDC, 300),
]
SEL_RUN = '0x9d759524'        # cast sig "run((address,address,address,address,uint8,uint8,uint8,bytes,uint256))"
SEL_EST = '0x406ba646'        # cast sig "getLiquidityEstimations()"
SEL_SLOT0 = '0x3850c7bd'      # cast sig "slot0()"
SEL_L1FEE = '0x49948e0e'      # cast sig "getL1Fee(bytes)"
TOPIC_MOVED = '0xc8333a73e4a1a16672a2dcb538b636e96b98466bfa9b61307c9860c9a94c608a'  # LiquidityMoved, from a receipt

MIN_DUR = 1500                # s after a move before the discount (about 0.28 pct per 1000 s) can cover gas
CU_LIMIT = 95_000
MAX_SEND_USD = 0.95
ETH_USD_CEILING = 6000.0      # only for the 0.95 USD per-send bound
MAX_GAS = 2_500_000
MAX_FEE_WEI = 60_000_000      # 0.06 gwei: 2.5M gas x 0.06 gwei = 0.00015 ETH
TIP_MAX_WEI = 3_000_000
BID_SHARE = 0.1               # at most this share of gross goes to the priority fee
LOG = HERE / 'logs/bot.jsonl'
STATE = HERE / 'state/cu.json'
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getBlockByNumber': 20,
           'eth_getTransactionReceipt': 20, 'eth_getLogs': 75}


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **data):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': round(time.time(), 3), 'ev': ev, **data}, separators=(',', ':')) + '\n')


def rpc(method, params):
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(STATE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    budget['cu'] += CU_COST.get(method, 26)
    if budget['cu'] > CU_LIMIT:
        raise ReadBudgetExceeded(f'{CU_LIMIT} CU/day cap')
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(budget))
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            ans = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise ReadBudgetExceeded('relay HTTP 429') from e
        raise
    if 'error' in ans:
        if any(s in str(ans['error']).lower() for s in ('cu cap', 'quota', 'budget exceeded', 'rate limit')):
            raise ReadBudgetExceeded(str(ans['error'])[:160])
        raise RuntimeError(f'{method}: {str(ans["error"])[:240]}')
    return ans['result']


def w(n):
    return format(n, '064x')


def a(addr):
    return addr.lower().removeprefix('0x').zfill(64)


_owner = None


def owner():
    global _owner
    if MODE == 'paper':
        return OWNER_PAPER
    if _owner is None:
        import farmbot_signer
        result = farmbot_signer.my_address()
        address = result['address'] if isinstance(result, dict) else result
        if not isinstance(address, str) or len(address) != 42:
            raise RuntimeError('signer my_address returned no address')
        _owner = address
    return _owner


def executor():
    return EXEC_LIVE if MODE == 'live' else EXEC_PAPER


def run_calldata(route, min_profit):
    _, torex, in_kind, out_kind, mode, raw, profit_token, _ = route
    n = len(raw) // 2
    return (SEL_RUN + w(32) + a(torex) + a(ROUTER) + a(WETH) + a(profit_token) + w(in_kind) + w(out_kind)
            + w(mode) + w(9 * 32) + w(min_profit) + w(n) + raw + '00' * ((-n) % 32))


def call_params(route, min_profit, gas=None):
    ex = executor()
    tx = {'from': owner(), 'to': ex, 'data': run_calldata(route, min_profit)}
    if gas is not None:
        tx['gas'] = hex(gas)
    params = [tx, 'latest']
    if MODE == 'paper':
        params.append({ex: {'code': RUNTIME.read_text().strip()}})
    return params


def simulate(route, min_profit, gas=None):
    """Profit of run() in the route's profit token (wei or USDC units); 0 when it reverts."""
    try:
        return int(rpc('eth_call', call_params(route, min_profit, gas)), 16), None
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        return 0, str(e)[:200]


def estimations(torex):
    r = rpc('eth_call', [{'to': torex, 'data': SEL_EST}, 'latest'])[2:]
    v = [int(r[i:i + 64], 16) for i in range(0, 256, 64)]
    return {'in_amount': v[0], 'min_out': v[1], 'duration': v[2], 'twap': v[3]}


_eth_usd = (0.0, 0.0)


def eth_usd():
    """USDC per ETH from the Uniswap V3 WETH/USDC 0.01 pct pool, refreshed hourly."""
    global _eth_usd
    if time.time() - _eth_usd[1] > 3600:
        r = rpc('eth_call', [{'to': POOL_WETH_USDC, 'data': SEL_SLOT0}, 'latest'])
        sqrt_p = int(r[2:66], 16)
        _eth_usd = ((sqrt_p / 2 ** 96) ** 2 * 1e12, time.time())
    return _eth_usd[0]


def to_wei(route, amount):
    """Profit in ETH wei, whatever the profit token."""
    return amount if route[6] == WETH else int(amount / 1e6 / eth_usd() * 1e18)


def l1_fee(data_hex):
    raw = data_hex[2:] + '00' * 110   # signature, nonce, gas fields of the signed tx
    n = len(raw) // 2
    r = rpc('eth_call', [{'to': L1_ORACLE, 'data': SEL_L1FEE + w(32) + w(n) + raw + '00' * ((-n) % 32)}, 'latest'])
    return int(r, 16)


def winner(torex, block):
    logs = rpc('eth_getLogs', [{'address': torex, 'topics': [TOPIC_MOVED],
                                'fromBlock': hex(max(0, block - 3000)), 'toBlock': hex(block + 10)}])
    if not logs:
        return None, None
    last = logs[-1]
    return int(last['blockNumber'], 16), '0x' + last['topics'][1][26:]


def send_live(route, gross_wei, cap_wei, min_profit, gas_limit, max_fee, tip):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC_LIVE, run_calldata(route, min_profit), 0,
                                gas_limit, max_fee, max_priority_fee_per_gas=tip)
    txh = reply.get('txHash') if isinstance(reply, dict) else None
    if not txh:
        log('signer_reject', route=route[0], reply=reply)
        return
    rc = None
    for _ in range(20):
        time.sleep(1.5)
        rc = rpc('eth_getTransactionReceipt', [txh])
        if rc:
            break
    if not rc:
        log('send_result', route=route[0], hash=txh, result='unknown', expected_gross_wei=gross_wei, cap_wei=cap_wei)
        return
    block = int(rc['blockNumber'], 16)
    won = int(rc['status'], 16) == 1
    used = int(rc['gasUsed'], 16)
    fee = int(rc['effectiveGasPrice'], 16)
    l1 = int(rc.get('l1Fee') or '0x0', 16)
    wblock, wmover = (block, executor()) if won else (None, None)
    if not won:
        try:
            wblock, wmover = winner(route[1], block)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('winner_lookup_error', hash=txh, error=str(e)[:160])
    log('send_result', route=route[0], hash=txh, result='won' if won else 'lost', gas_used=used,
        gas_cost_wei=used * fee + l1, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip,
        expected_gross_wei=gross_wei, cap_wei=cap_wei, send_block=block, tx_index=int(rc['transactionIndex'], 16),
        winner_block=wblock, winner_mover=wmover)


def check(route, st):
    """One look at one Torex. Returns seconds until the next look."""
    name, torex, poll = route[0], route[1], route[7]
    now = time.time()
    if st.get('resync', 0) <= now:
        est = estimations(torex)
        st['resync'] = now + 3600
        st['last_est'] = est
        if est['in_amount'] == 0 or est['duration'] < MIN_DUR:
            st['resync'] = 0
            log('wait', route=name, duration=est['duration'], in_amount=est['in_amount'])
            return max(60, MIN_DUR - est['duration'])
    gross, err = simulate(route, 1)
    if gross == 0:
        st['quiet'] = st.get('quiet', 0) + 1
        if st['quiet'] % 30 == 1:
            log('check', route=name, result='no_profit', error=err)
        if st['quiet'] % 5 == 0:
            st['resync'] = 0          # maybe someone moved it: re-read the duration
        return poll
    gross_wei = to_wei(route, gross)
    base = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    # cheap pre-check with the fork-measured 1.93M gas before spending an estimate
    if gross_wei < 1_900_000 * base:
        st['quiet'] = st.get('quiet', 0) + 1
        if st['quiet'] % 10 == 1:
            log('check', route=name, result='below_gas', gross=gross, gross_wei=gross_wei, base_fee=base)
        return poll
    st['quiet'] = 0
    try:
        estimate = int(rpc('eth_estimateGas', call_params(route, 1)), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', route=name, step='estimate', error=str(e)[:200])
        return poll
    gas_limit = estimate * 110 // 100
    tip = min(TIP_MAX_WEI, int(gross_wei * BID_SHARE / gas_limit))
    max_fee = base * 11 // 10 + tip
    l1 = l1_fee(run_calldata(route, 1))
    cap_wei = gas_limit * max_fee + l1 * 12 // 10
    cap_usd = cap_wei / 1e18 * ETH_USD_CEILING
    log('opportunity', route=name, gross=gross, gross_wei=gross_wei, cap_wei=cap_wei, gas_estimate=estimate,
        gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip, l1_fee_wei=l1, eth_usd=round(eth_usd(), 2))
    if gas_limit > MAX_GAS or max_fee > MAX_FEE_WEI or cap_usd >= MAX_SEND_USD or gross_wei <= cap_wei:
        log('opportunity_skip', route=name, reason='gross_not_above_gas_cap_or_limits', gross_wei=gross_wei,
            cap_wei=cap_wei, gas_limit=gas_limit, max_fee_wei=max_fee)
        return poll
    # the executor itself reverts below half of the simulated profit
    min_profit = max(1, gross // 2)
    checked, err = simulate(route, min_profit, gas_limit)
    if checked < min_profit:
        log('simulate_revert', route=name, step='profit_guard', error=err)
        return poll
    if MODE == 'paper':
        log('paper_sim', route=name, result='success', gross=checked, gross_wei=to_wei(route, checked),
            cap_wei=cap_wei, gas_estimate=estimate, min_profit=min_profit,
            duration=(st.get('last_est') or {}).get('duration'))
        st['resync'] = 0
        return 600                    # paper cannot take it: do not log the same case every poll
    send_live(route, gross_wei, cap_wei, min_profit, gas_limit, max_fee, tip)
    st['resync'] = 0
    return 60


def main():
    if not RELAY:
        raise SystemExit('RPC_RELAY_URL required')
    if MODE == 'live' and not EXEC_LIVE:
        raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR required')
    if MODE == 'paper' and not RUNTIME.exists():
        raise SystemExit('missing executor-runtime.hex')
    log('start', mode=MODE, executor=executor(), routes=[r[0] for r in ROUTES])
    states = [{'next': 0.0} for _ in ROUTES]
    while True:
        try:
            for route, st in zip(ROUTES, states):
                if st['next'] > time.time():
                    continue
                try:
                    st['next'] = time.time() + check(route, st)
                except ReadBudgetExceeded:
                    raise
                except Exception as e:
                    log('check_error', route=route[0], error=str(e)[:300])
                    st['next'] = time.time() + route[7]
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            tomorrow = (now + datetime.timedelta(days=1)).date()
            wake = datetime.datetime.combine(tomorrow, datetime.time(), datetime.timezone.utc)
            time.sleep(max(1, (wake - now).total_seconds()))
        time.sleep(max(1.0, min(st['next'] for st in states) - time.time()))


if __name__ == '__main__':
    main()
