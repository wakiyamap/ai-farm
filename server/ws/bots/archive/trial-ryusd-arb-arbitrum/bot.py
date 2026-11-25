#!/usr/bin/env python3
"""trial: Sommelier Real Yield USD cellar on Arbitrum. The cellar's public multiAssetDeposit takes USDC.e, USDT or
DAI at its price router's value (deposit fee 0) and its public redeem pays out in the same transaction. When one of
those stablecoins is cheaper in its Uniswap V3 USDC pool than the cellar's price, one Morpho-flash-funded transaction
through the StepArb executor does: USDC -> stablecoin (Uniswap V3) -> multiAssetDeposit -> redeem -> [sell back to
USDC whatever the redeem paid in kind] -> repay, and keeps the rest as USDC.
Timer bot: one probe() eth_call every POLL seconds (the stablecoin pools are busy: no feed filter on them)."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'arbitrum'

# Addresses: each checked with a getter (README, "Addresses"; scratch/r47c8/cellars.py, rcpt.py).
MORPHO = '0x6c247b1F6182318877311737BaC0844bAa518F5e'    # Morpho Blue, flashLoan(token, assets, data), no fee
USDC = '0xaf88d065e77c8cC2239327C5EDb3A432268e5831'
USDCE = '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'
USDT = '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'
DAI = '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1'
CELLAR = '0x392B1E6905bb8449d26af701Cdea6Ff47bF6e5A8'    # Real Yield USD (verified CellarWith...MultiAssetDeposit)
UNIV3 = '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'     # Uniswap V3 SwapRouter02 (factory() = 0x1F98431c...)
POOL_WETH_USDC = '0xC6962004f452bE9203591991D15f6b388e09E8D0'   # Uniswap V3 0.05 pct, token0 WETH: ETH price for the gas cap
# route name -> (stablecoin deposited, Uniswap V3 fee tier of its USDC pool)
ROUTES = {'usdce': (USDCE, 100), 'usdt': (USDT, 100), 'dai': (DAI, 100)}
ALTS = (USDCE, USDT, DAI)

# Selectors, all from `cast sig` (scratch/trial-ryusd-arb-arbitrum/proof.py asserts them).
SEL_TAKE = '0x13b75307'      # take(address,address,uint256,(address,address,address,uint256,uint256,bytes)[],address[],uint256,bool)
SEL_V3 = '0x04e45aaf'        # exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))
SEL_MADEPOSIT = '0x2b91c5de' # multiAssetDeposit(address,uint256,address)
SEL_REDEEM = '0xba087652'    # redeem(uint256,address,address)
SEL_PROBE = '0x8ad8bbaf'     # probe(bytes[])
SEL_SLOT0 = '0x3850c7bd'     # slot0()
TOPIC_MADEPOSIT = '0x385ba312edecbeeae57aca70f4fde3d83578697795291e74b1b4edb37d7291bf'   # MultiAssetDeposit(address,address,address,uint256,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000f11a9'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

SIZES_USDC = (500, 1500, 4000, 9000, 18000)   # USDC flash sizes (the cellar holds about 21,000 USDC)
CLEAR = (USDCE, USDT, DAI, CELLAR)
MIN_INTEREST = 20_000             # 0.02 USDC: below this a take cannot cover its gas
POLL = 120                        # seconds between probes
FOLLOW_UPS = (10, 30)             # seconds after a look that left a gain standing below the send line
TIP_WEI = 0                       # Arbitrum orders by arrival: no priority fee, never raised
MAX_FEE_CAP_WEI = 5 * 10**8       # 0.5 gwei: never sign above this
GAS_LIMIT_MAX = 4_000_000
ETH_REF_USD = 4000.0              # conservative (about 1,650 USD on 2026-11-21), only for the 0.95 USD bound
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


# ---- ABI encoding (static words and the one dynamic shape take() needs) ----
def w(n):
    return format(n, '064x')


def a(addr):
    return addr.lower().removeprefix('0x').zfill(64)


def step(target, token_in, spender, data, offset, amount=0):
    return {'target': target, 'tokenIn': token_in or '0x' + '00' * 20,
            'spender': spender or '0x' + '00' * 20, 'amount': amount, 'offset': offset, 'data': data}


def swap_step(token_in, token_out, fee, to):
    # exactInputSingle((tokenIn, tokenOut, fee, recipient, amountIn, amountOutMinimum, sqrtPriceLimitX96)), whole balance
    return step(UNIV3, token_in, UNIV3, SEL_V3 + a(token_in) + a(token_out) + w(fee) + a(to) + w(0) + w(0) + w(0), 4 + 4 * 32)


def route_steps(name, to):
    alt, fee = ROUTES[name]
    steps = [
        swap_step(USDC, alt, fee, to),
        # multiAssetDeposit(depositAsset, assets, receiver): the whole balance, shares to the executor
        step(CELLAR, alt, CELLAR, SEL_MADEPOSIT + a(alt) + w(0) + a(to), 4 + 32),
        # redeem(shares, receiver, owner): the whole share balance (no approval: owner = msg.sender)
        step(CELLAR, CELLAR, None, SEL_REDEEM + w(0) + a(to) + a(to), 4),
    ]
    # the cellar redeems in kind, in its withdraw order: sell back whatever is not USDC (StepArb skips a step whose
    # tokenIn balance is 0)
    for t in ALTS:
        steps.append(swap_step(t, USDC, 100, to))
    return steps


def enc_step(s):
    data = bytes.fromhex(s['data'].removeprefix('0x'))
    pad = (-len(data)) % 32
    return (a(s['target']) + a(s['tokenIn']) + a(s['spender']) + w(s['amount']) + w(s['offset'])
            + w(6 * 32) + w(len(data)) + data.hex() + '00' * pad)


def take_calldata(name, amount, min_profit, executor):
    steps = [enc_step(s) for s in route_steps(name, executor)]
    offs, pos = [], 32 * len(steps)
    for s in steps:
        offs.append(pos)
        pos += len(s) // 2
    steps_blob = w(len(steps)) + ''.join(w(o) for o in offs) + ''.join(steps)
    clear_blob = w(len(CLEAR)) + ''.join(a(t) for t in CLEAR)
    head = 7 * 32
    # unwrap = false: the gain is paid to the owner as USDC
    return (SEL_TAKE + a(MORPHO) + a(USDC) + w(amount) + w(head) + w(head + len(steps_blob) // 2)
            + w(min_profit) + w(0) + steps_blob + clear_blob)


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


def probe_calldata(calls):
    """probe(bytes[]) with one take() calldata per candidate."""
    blobs = []
    for c in calls:
        raw = c.removeprefix('0x')
        blobs.append(w(len(raw) // 2) + raw + '00' * ((-(len(raw) // 2)) % 32))
    offs, pos = [], 32 * len(blobs)
    for b in blobs:
        offs.append(pos)
        pos += len(b) // 2
    return SEL_PROBE + w(32) + w(len(blobs)) + ''.join(w(o) for o in offs) + ''.join(blobs)


def candidates():
    return [(name, size * 10**6) for name in ROUTES for size in SIZES_USDC]


def call_params(name, amount, min_profit, gas_limit=None, block='latest', data=None):
    ex = executor()
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': ex,
          'data': data or take_calldata(name, amount, min_profit, ex)}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx, block]
    if MODE == 'paper':
        params.append({ex: {'code': RUNTIME_FILE.read_text().strip()}})
    return params


def probe(cands, block='latest'):
    """Gains (USDC units) of every (route, amount) candidate in ONE eth_call; 0 = that take would revert."""
    ex = executor()
    data = probe_calldata([take_calldata(n, amt, 1, ex) for n, amt in cands])
    res = rpc('eth_call', call_params(None, 0, 0, None, block, data))
    words = [int(res[2 + i:2 + i + 64], 16) for i in range(0, len(res) - 2, 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(cands):
        raise RuntimeError('probe: unexpected return length')
    return gains


def gain_of(name, amount, min_profit=1, gas_limit=None, block='latest'):
    """Gain in USDC units of take() as an eth_call; 0 when it reverts (NoProfit or a failed step)."""
    ans = rpc('eth_call', call_params(name, amount, min_profit, gas_limit, block), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def fees():
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    return base_fee, base_fee + base_fee // 4 + TIP_WEI


_eth_usd = (0.0, 0.0)


def eth_usd():
    """USDC per ETH from the Uniswap V3 WETH/USDC 0.05 pct pool, refreshed every 30 min."""
    global _eth_usd
    if time.time() - _eth_usd[1] > 1800:
        r = rpc('eth_call', [{'to': POOL_WETH_USDC, 'data': SEL_SLOT0}, 'latest'])
        _eth_usd = ((int(r[2:66], 16) / 2**96) ** 2 * 1e12, time.time())
    return _eth_usd[0]


def last_take_block(block):
    """Block of the newest MultiAssetDeposit on the cellar near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': CELLAR, 'fromBlock': hex(block - 400), 'toBlock': hex(block + 20),
                                'topics': [TOPIC_MADEPOSIT]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(name, amount, gross, min_profit, cap, max_fee, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(name, amount, min_profit, EXEC), 0, gas_limit,
                                max_fee, max_priority_fee_per_gas=TIP_WEI)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', reply=reply)
        return
    receipt = None
    for _ in range(20):
        time.sleep(1.5)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=tx_hash, result='unknown', route=name, amount_usdc=amount, expected_gross_usdc=gross,
            cap_wei=cap, gas_limit=gas_limit, max_fee_wei=max_fee, gas_used=None, winner_block=None)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        winner = block if status else last_take_block(block)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', hash=tx_hash, result='won' if status else 'lost', route=name, amount_usdc=amount,
        gas_used=used, gas_limit=gas_limit, max_fee_wei=max_fee, cap_wei=cap, gas_cost_wei=cost,
        expected_gross_usdc=gross if status else 0, min_profit_usdc=min_profit,
        send_block=block, winner_block=winner, tx_index=int(receipt['transactionIndex'], 16))


def check(trigger='manual'):
    """One look. Returns True when a gain was seen (taken or not): the caller schedules follow-up looks."""
    cands = candidates()
    gains = probe(cands)
    gross = max(gains)
    name, amount = cands[gains.index(gross)]
    if gross < MIN_INTEREST:
        log('check', trigger=trigger, result='no_gain', best_usdc=gross, best_route=name if gross else None)
        return False
    base_fee, max_fee = fees()
    if max_fee > MAX_FEE_CAP_WEI:
        log('opportunity_skip', trigger=trigger, reason='fee_cap', route=name, gross_usdc=gross, base_fee=base_fee)
        return True
    try:
        estimate = int(rpc('eth_estimateGas', call_params(name, amount, 1)), 16)   # Arbitrum: always from eth_estimateGas
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', trigger=trigger, step='estimate', route=name, gross_usdc=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 12 // 10
    cap = gas_limit * max_fee                     # the most this send can cost, wei
    price = eth_usd()
    cap_usdc = int(cap / 1e18 * price * 1e6) + 1  # the same in USDC units at the pool price
    cap_usd = cap / 1e18 * ETH_REF_USD
    log('opportunity', trigger=trigger, route=name, amount_usdc=amount, gross_usdc=gross, cap_wei=cap, cap_usdc=cap_usdc,
        eth_usd=round(price, 2), base_fee=base_fee, max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit)
    if gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='gas_limit_or_usd_cap', route=name, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross <= cap_usdc:                         # send only when expected gross > this send's gas cap
        log('opportunity_skip', reason='gross_not_above_gas_cap', route=name, gross_usdc=gross, cap_usdc=cap_usdc)
        return True
    checked, err = gain_of(name, amount, cap_usdc, gas_limit)   # the exact call that would be signed
    if checked <= cap_usdc:
        log('simulate_revert', step='guard', route=name, gross_usdc=gross, cap_usdc=cap_usdc, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', trigger=trigger, route=name, amount_usdc=amount, gross_usdc=checked,
            cap_wei=cap, cap_usdc=cap_usdc, gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee,
            tip_wei=TIP_WEI)
    else:
        send_live(name, amount, checked, cap_usdc, cap, max_fee, gas_limit)
    return True                                   # look again: part of the gap may be left, or the send lost


def main():
    """Timer loop. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), routes=list(ROUTES), sizes_usdc=list(SIZES_USDC),
        poll_seconds=POLL, follow_ups=list(FOLLOW_UPS))
    follow_ups = []
    next_poll = 0
    while True:
        try:
            now = time.time()
            if follow_ups and now >= follow_ups[0]:
                follow_ups = follow_ups[1:]
                check('follow_up')
            elif now >= next_poll:
                next_poll = now + POLL
                seen = check('timer')
                # follow-ups only live (after a send, part of the gap may be left); in paper a gap nobody takes
                # would otherwise triple the read cost
                follow_ups = [time.time() + d for d in FOLLOW_UPS] if (seen and MODE == 'live') else []
            else:
                time.sleep(max(0.5, min([next_poll] + follow_ups[:1]) - now))
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            follow_ups = []
            now = datetime.datetime.now(datetime.timezone.utc)
            time.sleep(86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 5)   # to 00:00 UTC
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            next_poll = time.time() + POLL
            time.sleep(5)


if __name__ == '__main__':
    main()
