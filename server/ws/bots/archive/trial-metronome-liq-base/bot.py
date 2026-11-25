#!/usr/bin/env python3
"""trial: Metronome Synth (Base) liquidations through the MetroLiq executor, one transaction, Morpho flash loan.

Timer bot: one Multicall3 eth_call per poll reads Pool.debtPositionOf for every tracked debtor. When a position is
unhealthy it sizes the liquidation by simulating the executor, and sends only when the simulated gain is above the
signed gas cap. Paper mode simulates with a code override and sends nothing.
"""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'base'

# Addresses: Metronome deployment read on chain (Pool.getDepositTokens / getDebtTokens, underlying(), token()),
# Morpho / pools from winner traces 0x95912733... and 0x868a829f..., exit pools from UniswapV3Factory.getPool.
POOL = '0xc614136d6c5ab85bc2acf0ec2652351642d7f54e'
MORPHO = '0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb'
WETH = '0x4200000000000000000000000000000000000006'
MC3 = '0xcA11bde05977b3631167028862bE2a173976CA11'
MSETH = '0x7Ba6F01772924a82D9626c126347A28299E98c98'
MSUSD = '0x526728DBc96689597F85ae4cd716d4f7fCcBAE9d'
BRIDGE_POOL = '0x74f72788F4814D7fF3C49B44684aa98Eee140C0E'  # Slipstream WETH/msETH
ZERO = '0x' + '0' * 40
USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
WSTETH = '0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452'
CBETH = '0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22'
DEBT_TOKENS = {'0x7bcC1DEcCaa98D52Bf89485f17a3E8607011cFde': MSUSD, '0x6F622b037F9146bdE102db84FC9152dF1042aa98': MSETH}
DEBT_START_BLOCK = 14_104_186   # creation block of msETH-Debt-1 (explorer)
EXIT_POOLS = {
    WETH: [ZERO],
    USDC: ['0xd0b53D9277642d899DF5C87A3966A349A798F224', '0x6c561B446416E1A00E8E93E221854d6eA4171372'],
    WSTETH: ['0x20E068D76f9E90b90604500B84c7e19dCB923e7e', '0x6f4482cBF7b43599078fcb012732e20480015644'],
    CBETH: ['0xA9DaFa443a02FBc907Cb0093276B3E6F4ef02A46', '0x10648BA41B8565907Cfa1496765fA4D95390aa0d'],
}
# deposit token -> (vault or ZERO, underlying after unwrapping)
DEPOSITS = {
    '0xC7F2f79Daa7Ea4FBbF60b45b5D6028BDE2453476': (ZERO, USDC),                                            # msdUSDC-1
    '0x8b581d0013F571a792c3Aa8AF2a0366A309BF51E': (ZERO, WETH),                                            # msdWETH-1
    '0x631E4eFe520152b9aa98aCa50739a7F6a8f21319': ('0x82562507429876486B60AF4F32390ef0947b3d13', WETH),    # msdvaETH-1
    '0x329846f9e19dAa7fD9844065a62eD01BCf63Cf69': ('0x1e41238aCd3A9fF90b0DCB9ea96Cf45F104e09Ef', USDC),    # msdvaUSDC-1
    '0x3E5C739deC75aC5b8BC11D763b02B2a777046802': ('0x46fb68Eb2b1Fc43654AbaE5691D39D18D933E4b4', WSTETH),  # msdvaWSTETH-1
    '0xE7Eb345866e07201f0dfe9Afb3a8f0637D998FC9': ('0x3899a6090c5C178dB8A1800DA39daD0D06EeEFBE', CBETH),   # msdvaCBETH-1
}

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment the runtime override was taken from
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000291'  # its constructor owner on the fork
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

# Selectors (cast sig) and topics (cast keccak)
SEL_LIQ = '0xdc7d2816'      # liquidate((address,address,uint256,address,address,address,address,address,uint256,address,address,address,address,uint256))
SEL_AGG3 = '0x82ad56cb'     # aggregate3((address,bool,bytes)[])
SEL_BAL = '0x70a08231'      # balanceOf(address)
SEL_POS = '0xdde3ab95'      # debtPositionOf(address)
SEL_QMAX = '0x984a68b5'     # quoteLiquidateMax(address,address,address)
SEL_QSWAPIN = '0x1ccfbc4f'  # quoteSwapIn(address,address,uint256)
T_TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
T_LIQUIDATED = '0xe1c3870e3d7d5199a16d200133088e6e3f7012d28571e442a110b4c83b5e3b94'  # PositionLiquidated(address,address,address,uint256,uint256,uint256)

POLL_SECONDS = 40
FAST_SECONDS = 10           # while a position is unhealthy or within FAST_RATIO of its limit
FAST_RATIO = 1.0005         # issuableLimit / debt
FAST_MIN_DEBT_USD = 20.0    # only positions this large switch the timer to fast
FAST_POLLS_PER_DAY = 1300   # 1300 x 26 CU = 34k CU/day at most for fast mode (3.6 hours of 10 s polling)
MIN_DEPOSIT_USD = 0.05      # an unhealthy position with less collateral than this is a bad-debt shell
TRACK_MIN_DEBT_USD = 1.0
CENSUS_SECONDS = 6 * 3600
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 115, 100
GAS_LIMIT_MAX = 2_600_000
BASE_FEE_HEADROOM_PCT = 5
MIN_TIP_WEI = 1_000_000          # 0.001 gwei
BID_SHARE_PCT = 30               # at most this share of the simulated gain is offered as priority fee
L1_ALLOWANCE_WEI = 100_000_000_000   # 30x the winner's L1 fee (3.35e9 wei, tx 0x95912733)
ETH_REF_USD = 4000.0             # deliberately high: the cap in wei stays under 1 USD at any ETH price below this
MAX_TX_USD = 0.90
MAX_LOST_PER_ACCOUNT_HOUR = 6
CU_CAP = 95_000
CU_COST = {'eth_call': 26, 'eth_getBlockByNumber': 20, 'eth_estimateGas': 20, 'eth_getLogs': 75,
           'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10}

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)


class ReadBudgetExceeded(Exception):
    pass


def log(event, **fields):
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': round(time.time(), 3), 'ev': event, **fields}, separators=(',', ':')) + '\n')


def rpc(method, params):
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
    STATE.write_text(json.dumps(budget))
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:240]}')
    return ans['result']


def w(n):
    return format(n, '064x')


def aw(addr):
    return addr.lower().removeprefix('0x').rjust(64, '0')


def agg3(calls):
    """One eth_call to Multicall3.aggregate3 with allowFailure. calls: [(target, calldata)] -> [(ok, hex)]."""
    elems = []
    for target, data in calls:
        b = data.removeprefix('0x')
        elems.append(aw(target) + w(1) + w(0x60) + w(len(b) // 2) + b + '0' * ((64 - len(b) % 64) % 64))
    offs, cur = [], 32 * len(elems)
    for e in elems:
        offs.append(w(cur))
        cur += len(e) // 2
    data = SEL_AGG3 + w(0x20) + w(len(elems)) + ''.join(offs) + ''.join(elems)
    r = rpc('eth_call', [{'to': MC3, 'data': data}, 'latest'])[2:]
    n = int(r[64:128], 16)
    out = []
    for i in range(n):
        o = 128 + 2 * int(r[128 + 64 * i:128 + 64 * (i + 1)], 16)
        ln = int(r[o + 128:o + 192], 16)
        out.append((int(r[o:o + 64], 16), r[o + 192:o + 192 + 2 * ln]))
    return out


_OWNER = None


def owner():
    """The bot wallet (live only), asked from the signer once."""
    global _OWNER
    if _OWNER is None:
        import farmbot_signer
        result = farmbot_signer.my_address()
        address = result['address'] if isinstance(result, dict) else result
        if not isinstance(address, str) or len(address) != 42:
            raise RuntimeError('signer my_address returned no address')
        _OWNER = address
    return _OWNER


def exec_addr():
    return EXEC if MODE == 'live' else PAPER_EXEC


def liq_calldata(c, min_profit):
    """c: candidate dict. Field order = MetroLiq.P."""
    return SEL_LIQ + ''.join([aw(MORPHO), aw(WETH), w(c['flash']), aw(POOL), aw(c['synth']), aw(MSETH), aw(BRIDGE_POOL),
                              aw(c['account']), w(c['repay']), aw(c['depositToken']), aw(c['vault']),
                              aw(c['underlying']), aw(c['exitPool']), w(min_profit)])


def call_params(c, min_profit, gas_limit=None):
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': exec_addr(), 'data': liq_calldata(c, min_profit)}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx, 'latest']
    if MODE == 'paper':
        params.append({PAPER_EXEC: {'code': RUNTIME}})
    return params


def simulate(c, min_profit, gas_limit=None):
    """The executor returns the WETH gain it would pay out; a revert raises."""
    return int(rpc('eth_call', call_params(c, min_profit, gas_limit)), 16)


def census():
    """All debtors from debt-token mint logs, kept when their debt is at least TRACK_MIN_DEBT_USD."""
    logs = rpc('eth_getLogs', [{'address': list(DEBT_TOKENS), 'fromBlock': hex(DEBT_START_BLOCK), 'toBlock': 'latest',
                                'topics': [T_TRANSFER, '0x' + '0' * 64]}])
    accounts = sorted({'0x' + l['topics'][2][-40:] for l in logs})
    tracked = []
    for i in range(0, len(accounts), 150):
        chunk = accounts[i:i + 150]
        res = agg3([(POOL, SEL_POS + aw(a)) for a in chunk])
        for a, (ok, ret) in zip(chunk, res):
            if ok and len(ret) >= 320 and int(ret[128:192], 16) >= TRACK_MIN_DEBT_USD * 1e18:
                tracked.append(a)
    log('census', mint_logs=len(logs), accounts=len(accounts), tracked=len(tracked))
    return tracked


def positions(tracked):
    res = agg3([(POOL, SEL_POS + aw(a)) for a in tracked])
    out = []
    for a, (ok, ret) in zip(tracked, res):
        if not ok or len(ret) < 320:
            continue
        v = [int(ret[64 * k:64 * (k + 1)], 16) for k in range(5)]
        out.append({'account': a, 'healthy': bool(v[0]), 'deposit_usd': v[1] / 1e18, 'debt_usd': v[2] / 1e18,
                    'limit_usd': v[3] / 1e18})
    return out


def candidates(account):
    """Every (debt synth, deposit token, exit pool, size) worth simulating for an unhealthy account."""
    synths = [MSUSD, MSETH]
    deps = list(DEPOSITS)
    calls = [(POOL, SEL_QMAX + aw(s) + aw(account) + aw(d)) for s in synths for d in deps]
    res = agg3(calls)
    out = []
    k = 0
    for s in synths:
        for d in deps:
            ok, ret = res[k]
            k += 1
            max_repay = int(ret[:64], 16) if ok and len(ret) >= 64 else 0
            if max_repay == 0:
                continue
            vault, underlying = DEPOSITS[d]
            # 99% first-class: the full quoteLiquidateMax can revert on rounding (the 0x868a829f winner repaid 99.0%)
            for num, den in ((1, 1), (99, 100), (1, 2), (1, 5), (1, 20)):
                repay = max_repay * num // den
                if repay == 0:
                    continue
                for exit_pool in EXIT_POOLS[underlying]:
                    out.append({'account': account, 'synth': s, 'repay': repay, 'max_repay': max_repay,
                                'depositToken': d, 'vault': vault, 'underlying': underlying, 'exitPool': exit_pool})
    # WETH to borrow: 1.5x the msETH needed at par (msETH has traded below WETH), read in one multicall for msUSD debt
    usd = [c for c in out if c['synth'] == MSUSD]
    if usd:
        res = agg3([(POOL, SEL_QSWAPIN + aw(MSETH) + aw(MSUSD) + w(c['repay'])) for c in usd])
        for c, (ok, ret) in zip(usd, res):
            c['flash'] = int(ret[:64], 16) * 3 // 2 if ok and len(ret) >= 64 else 0
    for c in out:
        if c['synth'] == MSETH:
            c['flash'] = c['repay'] * 3 // 2
    return [c for c in out if c.get('flash')]


def winner_lookup(account, block, tx_hash):
    latest = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': POOL, 'fromBlock': hex(max(0, block - 3000)), 'toBlock': hex(max(block, latest)),
                                'topics': [T_LIQUIDATED, None, '0x' + aw(account)]}])
    rivals = [l for l in logs if l['transactionHash'].lower() != tx_hash.lower() and int(l['blockNumber'], 16) <= block]
    if not rivals:
        return None, None
    last = rivals[-1]
    return int(last['blockNumber'], 16), last['transactionHash']


LOST = {}      # account -> timestamps of lost sends
BACKOFF = {}   # account -> unix time before which it is not looked at again


def send_live(c, gross, cap, max_fee, tip, min_profit, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, liq_calldata(c, min_profit), 0, gas_limit, max_fee,
                                max_priority_fee_per_gas=tip)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', account=c['account'], reply=reply)
        LOST.setdefault(c['account'], []).append(time.time())
        return
    log('send', hash=tx_hash, account=c['account'], gross_wei=gross, cap_wei=cap, gas_limit=gas_limit,
        max_fee_wei=max_fee, tip_wei=tip)
    receipt = None
    for _ in range(40):
        time.sleep(0.5)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=tx_hash, result='unknown', account=c['account'], gas_used=None, winner_block=None)
        LOST.setdefault(c['account'], []).append(time.time())
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee') or '0x0', 16)
    winner_block = winner_tx = None
    if not status:
        LOST.setdefault(c['account'], []).append(time.time())
        try:
            winner_block, winner_tx = winner_lookup(c['account'], block, tx_hash)
        except Exception as e:
            log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
    log('send_result', hash=tx_hash, result='won' if status else 'lost', account=c['account'], gas_used=used,
        gas_limit=gas_limit, gas_cost_wei=cost, expected_gross_wei=gross,
        net_wei=(gross - cost) if status else -cost, send_block=block, tx_index=int(receipt['transactionIndex'], 16),
        winner_block=winner_block, winner_tx=winner_tx,
        blocks_after_winner=(block - winner_block) if winner_block is not None else None)


def try_account(pos):
    account = pos['account']
    now = time.time()
    LOST[account] = [t for t in LOST.get(account, []) if now - t < 3600]
    if len(LOST[account]) >= MAX_LOST_PER_ACCOUNT_HOUR:
        log('opportunity_skip', reason='lost_limit', account=account)
        BACKOFF[account] = now + 900
        return
    cands = candidates(account)
    best, best_gross, errors = None, 0, 0
    for c in cands:
        try:
            gross = simulate(c, 1)
        except Exception:
            errors += 1
            continue
        if gross > best_gross:
            best, best_gross = c, gross
    if best is None:
        log('opportunity_skip', reason='no_profitable_route', account=account, debt_usd=pos['debt_usd'],
            deposit_usd=pos['deposit_usd'], candidates=len(cands), sim_errors=errors)
        BACKOFF[account] = now + 600
        return
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(best, 1)), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', account=account, error=str(e)[:200])
        BACKOFF[account] = time.time() + 60
        return
    gas_limit = estimate * GAS_MARGIN_NUM // GAS_MARGIN_DEN
    # priority fee: up to BID_SHARE_PCT of the simulated gain, spread over the gas limit, inside the 0.90 USD cap
    max_fee_cap = int(MAX_TX_USD / ETH_REF_USD * 1e18 - L1_ALLOWANCE_WEI) // gas_limit
    floor_fee = base_fee + base_fee * BASE_FEE_HEADROOM_PCT // 100
    tip = max(MIN_TIP_WEI, best_gross * BID_SHARE_PCT // 100 // gas_limit)
    tip = min(tip, max(0, max_fee_cap - floor_fee))
    max_fee = floor_fee + tip
    cap = gas_limit * max_fee + L1_ALLOWANCE_WEI
    info = dict(account=account, synth=best['synth'], depositToken=best['depositToken'], exitPool=best['exitPool'],
                repay=best['repay'], max_repay=best['max_repay'], gross_wei=best_gross, cap_wei=cap, base_fee=base_fee,
                max_fee_wei=max_fee, tip_wei=tip, gas_estimate=estimate, gas_limit=gas_limit, debt_usd=pos['debt_usd'])
    log('opportunity', **info)
    if gas_limit > GAS_LIMIT_MAX or tip < MIN_TIP_WEI or cap / 1e18 * ETH_REF_USD >= MAX_TX_USD:
        log('opportunity_skip', reason='gas_or_usd_cap', **info)
        BACKOFF[account] = now + 300
        return
    if best_gross <= cap:
        log('opportunity_skip', reason='gross_not_above_signed_gas_cap', **info)
        BACKOFF[account] = now + 300
        return
    min_profit = cap + 1
    try:
        checked = simulate(best, min_profit, gas_limit)
    except Exception as e:
        log('simulate_revert', account=account, error=str(e)[:200], gas_limit=gas_limit)
        BACKOFF[account] = now + 60
        return
    if checked <= cap:
        log('opportunity_skip', reason='guard_sim_below_cap', account=account, gross_wei=checked, cap_wei=cap)
        BACKOFF[account] = now + 60
        return
    if MODE == 'paper':
        log('paper_sim', result='success', **{**info, 'gross_wei': checked})
        BACKOFF[account] = now + 600   # paper: do not re-simulate the same case every poll
    else:
        send_live(best, checked, cap, max_fee, tip, min_profit, gas_limit)


def main():
    log('start', mode=MODE, executor=exec_addr(), pool=POOL, poll_seconds=POLL_SECONDS, fast_seconds=FAST_SECONDS)
    tracked, census_at, polls = [], 0.0, 0
    fast_day, fast_polls = None, 0
    while True:
        started = time.monotonic()
        delay = POLL_SECONDS
        try:
            if not tracked or time.time() - census_at > CENSUS_SECONDS:
                tracked = census()
                census_at = time.time()
            pos = positions(tracked)
            now = time.time()
            # unhealthy with collateral left to seize (bad-debt shells have none) and not backed off
            unhealthy = [p for p in pos if not p['healthy'] and p['deposit_usd'] >= MIN_DEPOSIT_USD
                         and now >= BACKOFF.get(p['account'], 0)]
            ratios = sorted((p['limit_usd'] / p['debt_usd'], p['account'], p['debt_usd']) for p in pos
                            if p['healthy'] and p['debt_usd'] >= FAST_MIN_DEBT_USD)
            near = ratios[0] if ratios else None
            if polls % 30 == 0 or unhealthy:
                log('check', tracked=len(pos), unhealthy=len(unhealthy),
                    nearest_ratio=round(near[0], 5) if near else None, nearest_account=near[1] if near else None,
                    nearest_debt_usd=round(near[2], 2) if near else None)
            polls += 1
            for p in sorted(unhealthy, key=lambda x: -x['debt_usd'])[:3]:
                try_account(p)
            if unhealthy or (near and near[0] < FAST_RATIO):
                day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
                if day != fast_day:
                    fast_day, fast_polls = day, 0
                if fast_polls < FAST_POLLS_PER_DAY:
                    fast_polls += 1
                    delay = FAST_SECONDS
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            delay = 1800
        except Exception as e:
            log('check_error', error=str(e)[:300])
        time.sleep(max(1, delay - (time.monotonic() - started)))


if __name__ == '__main__':
    main()
