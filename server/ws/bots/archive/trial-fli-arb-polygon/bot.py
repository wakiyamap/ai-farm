#!/usr/bin/env python3
"""trial: ETH2x-FLI-P (Index Coop SetToken, Polygon) issue / redeem versus its SushiSwap pair and the
Curve aToken venues, one flash-funded transaction through the StepArb executor. Timer bot, no feed."""
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
CHAIN = 'polygon'

# Addresses: explorer-verified contracts and the incumbents' traced route (README, "Addresses").
MORPHO = '0x1bF0c2541F820E775182832f06c0B7Fc27A25f67'   # Morpho Blue, flashLoan(token, assets, data)
WPOL = '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270'
WETH = '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619'
USDCE = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
CRV = '0x172370d5Cd63279eFa6d502DAB29171933a610AF'
MAI = '0xa3Fa99A148fA48D14Ed51d610c367C61876997F1'
AMWETH = '0x28424507fefb6f7f8E9D3860F56504E4e5f5f390'  # Aave v2 Polygon aToken (market frozen)
AM3CRV = '0xE7a24EF0C5e95Ffb0f6684b813A78F2a3AD7D171'  # Curve aave pool LP
TRILP = '0xdAD97F7713Ae9437fa9249920eC8507e5FbB23d3'   # Curve atricrypto3 LP
FLI = '0x3Ad707dA309f3845cd602059901E39C4dcd66473'      # ETH2x-FLI-P SetToken
MODULE = '0xf2dC2f456b98Af9A6bEEa072AF152a7b0EaA40C9'  # DebtIssuanceModuleV2
SUSHI = '0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506'   # SushiSwap router
UNIV3 = '0xE592427A0AEce92De3Edee1F18E0157C05861564'   # Uniswap V3 SwapRouter
TRI = '0x92215849c439E1f8612b6646060B4E3E5ef822cC'     # Curve atricrypto3 pool (am3CRV, amWBTC, amWETH)
CRVPOOL = '0xc7c939A474CB10EB837894D1ed1a77C61B268Fa7' # Curve CRV / atricrypto3-LP pool
MAIPOOL = '0x447646e84498552e62eCF097Cc305eaBFFF09308' # Curve MAI / am3CRV metapool
AAVE2 = '0x8dFf5E27EA6b7AC08EbFdf9eB090F32ee9a30fcf'   # Aave v2 LendingPool (withdraw only)

# Selectors, all from `cast sig` and all seen in the incumbents' traces.
SEL_TAKE = '0xb62fbc15'      # take(address,address,uint256,(uint8,address,address,address,uint256,uint256,bytes)[],address[],uint256,bool)
SEL_V3 = '0x414bf389'        # exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))
SEL_CEX = '0x5b41b908'       # exchange(uint256,uint256,uint256,uint256)
SEL_SEX = '0x3df02124'       # exchange(int128,int128,uint256,uint256)
SEL_RM1 = '0xf1dc3cc9'       # remove_liquidity_one_coin(uint256,uint256,uint256)
SEL_ADD3 = '0x4515cef3'      # add_liquidity(uint256[3],uint256)
SEL_REDEEM = '0x5c833bfd'    # redeem(address,uint256,address)
SEL_V2 = '0x38ed1739'        # swapExactTokensForTokens(uint256,uint256,address[],address,uint256)
SEL_WITHDRAW = '0x69328dec'  # withdraw(address,uint256,address)
SEL_PROBE = '0x8ad8bbaf'     # probe(bytes[])

PAPER_EXEC = '0x00000000000000000000000000000000000f11a5'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000301'
EXEC = os.environ.get('EXECUTOR_ADDR_POLYGON') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_POLYGON or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

MAXU = (1 << 256) - 1
DEADLINE = 0xffffffffff
DUST_WPOL = 2 * 10**17            # swapped to USDC.e for the SetToken's 56-unit USDC component
SIZES = (500, 1000, 2000)         # WPOL flash sizes tried per route; the incumbents use 900-1,800
MIN_INTEREST_WEI = 5 * 10**17     # below 0.5 WPOL a take cannot cover its gas: no estimate, no log line
POLL_SECONDS = 30                 # one probe eth_call (all routes and sizes) per poll
_quiet = 0
TIP_WEI = 30 * 10**9              # Polygon's minimum priority fee
MAX_FEE_CAP_WEI = 1500 * 10**9    # never sign above this
GAS_LIMIT_MAX = 4_500_000
POL_REF_USD = 0.15                # conservative (measured 0.083 USD on 2026-11-19)
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


def v3(token_in, token_out, fee, to):
    return SEL_V3 + a(token_in) + a(token_out) + w(fee) + a(to) + w(DEADLINE) + w(0) + w(0) + w(0)


V3_OFF = 4 + 5 * 32


def step(target, token_in, spender, data, offset, amount=0, kind=0):
    return {'kind': kind, 'target': target, 'tokenIn': token_in or '0x' + '00' * 20,
            'spender': spender or '0x' + '00' * 20, 'amount': amount, 'offset': offset, 'data': data}


def v3_step(token_in, token_out, fee, to, amount=0):
    return step(UNIV3, token_in, UNIV3, v3(token_in, token_out, fee, to), V3_OFF, amount)


def v2_step(token_in, token_out, to):
    data = SEL_V2 + w(0) + w(0) + w(0xa0) + a(to) + w(DEADLINE) + w(2) + a(token_in) + a(token_out)
    return step(SUSHI, token_in, SUSHI, data, 4)


def tail_steps(to):
    """Leftovers back to WPOL: aToken dust -> WETH, WETH -> WPOL, USDC.e -> WPOL. Zero balances are skipped."""
    return [step(AAVE2, AMWETH, None, SEL_WITHDRAW + a(WETH) + w(MAXU) + a(to), MAXU),
            v3_step(WETH, WPOL, 500, to),
            v3_step(USDCE, WPOL, 500, to)]


def route_steps(name, amount, to):
    issue = step(MODULE, None, None, '0x' + a(FLI), MAXU, kind=1)
    redeem = step(MODULE, FLI, None, SEL_REDEEM + a(FLI) + w(0) + a(to), 4 + 32)
    if name == 'issue_crv':     # WPOL -> CRV -> atricrypto3 LP -> amWETH -> issue -> Sushi
        return [v3_step(WPOL, USDCE, 500, to, DUST_WPOL),
                v3_step(WPOL, CRV, 3000, to),
                step(CRVPOOL, CRV, CRVPOOL, SEL_CEX + w(0) + w(1) + w(0) + w(0), 4 + 64),
                step(TRI, TRILP, TRI, SEL_RM1 + w(0) + w(2) + w(0), 4),
                issue, v2_step(FLI, WETH, to)] + tail_steps(to)
    if name == 'issue_mai':     # WPOL -> USDC.e -> MAI -> am3CRV -> amWETH -> issue -> Sushi
        return [v3_step(WPOL, USDCE, 500, to, amount - DUST_WPOL),
                v3_step(USDCE, MAI, 100, to),
                step(MAIPOOL, MAI, MAIPOOL, SEL_SEX + w(0) + w(1) + w(0) + w(0), 4 + 64),
                step(TRI, AM3CRV, TRI, SEL_CEX + w(0) + w(2) + w(0) + w(0), 4 + 64),
                v3_step(WPOL, USDCE, 500, to),
                issue, v2_step(FLI, WETH, to)] + tail_steps(to)
    if name == 'redeem_mai':    # Sushi -> redeem -> amWETH -> am3CRV -> MAI -> USDC.e
        return [v3_step(WPOL, WETH, 500, to), v2_step(WETH, FLI, to), redeem,
                step(TRI, AMWETH, TRI, SEL_CEX + w(2) + w(0) + w(0) + w(0), 4 + 64),
                step(MAIPOOL, AM3CRV, MAIPOOL, SEL_SEX + w(1) + w(0) + w(0) + w(0), 4 + 64),
                v3_step(MAI, USDCE, 100, to)] + tail_steps(to)
    if name == 'redeem_crv':    # Sushi -> redeem -> amWETH -> atricrypto3 LP -> CRV
        return [v3_step(WPOL, WETH, 500, to), v2_step(WETH, FLI, to), redeem,
                step(TRI, AMWETH, TRI, SEL_ADD3 + w(0) + w(0) + w(0) + w(0), 4 + 64),
                step(CRVPOOL, TRILP, CRVPOOL, SEL_CEX + w(1) + w(0) + w(0) + w(0), 4 + 64),
                v3_step(CRV, WPOL, 3000, to)] + tail_steps(to)
    raise ValueError(name)


ROUTES = ('issue_crv', 'issue_mai', 'redeem_mai', 'redeem_crv')
CLEAR = (WETH, USDCE, AMWETH, FLI, CRV, MAI, AM3CRV, TRILP)


def enc_step(s):
    data = bytes.fromhex(s['data'].removeprefix('0x'))
    pad = (-len(data)) % 32
    return (w(s['kind']) + a(s['target']) + a(s['tokenIn']) + a(s['spender']) + w(s['amount']) + w(s['offset'])
            + w(7 * 32) + w(len(data)) + data.hex() + '00' * pad)


def take_calldata(name, amount, min_profit, executor):
    steps = [enc_step(s) for s in route_steps(name, amount, executor)]
    offs, pos = [], 32 * len(steps)
    for s in steps:
        offs.append(pos)
        pos += len(s) // 2
    steps_blob = w(len(steps)) + ''.join(w(o) for o in offs) + ''.join(steps)
    clear_blob = w(len(CLEAR)) + ''.join(a(t) for t in CLEAR)
    head = 7 * 32
    return (SEL_TAKE + a(MORPHO) + a(WPOL) + w(amount) + w(head) + w(head + len(steps_blob) // 2)
            + w(min_profit) + w(1) + steps_blob + clear_blob)


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


def probe(cands, block='latest'):
    """Gains (WPOL wei) of every (route, amount) candidate in ONE eth_call; 0 = that take would revert."""
    ex = executor()
    data = probe_calldata([take_calldata(n, amt, 1, ex) for n, amt in cands])
    res = rpc('eth_call', call_params(None, 0, 0, None, block, data))
    words = [int(res[2 + i:2 + i + 64], 16) for i in range(0, len(res) - 2, 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(cands):
        raise RuntimeError('probe: unexpected return length')
    return gains


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


def gain_of(name, amount, min_profit=1, gas_limit=None, block='latest'):
    """Gain in WPOL wei of take() as an eth_call; 0 when it reverts (NoProfit or a failed step)."""
    ans = rpc('eth_call', call_params(name, amount, min_profit, gas_limit, block), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def fees():
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    return base_fee, base_fee + base_fee // 4 + TIP_WEI


def last_issue_or_redeem_block(block):
    logs = rpc('eth_getLogs', [{'address': MODULE, 'fromBlock': hex(block - 60), 'toBlock': hex(block + 5)}])
    hits = [int(x['blockNumber'], 16) for x in logs if len(x['topics']) > 1 and x['topics'][1][-40:] == FLI.lower()[2:]]
    return max(hits, default=None)


def send_live(name, amount, gross, cap, max_fee, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(name, amount, cap, EXEC), 0, gas_limit,
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
        log('send_result', hash=tx_hash, result='unknown', route=name, amount_wei=amount, expected_gross_wei=gross,
            cap_wei=cap, gas_limit=gas_limit, max_fee_wei=max_fee, gas_used=None, winner_block=None)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        winner = block if status else last_issue_or_redeem_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', hash=tx_hash, result='won' if status else 'lost', route=name, amount_wei=amount,
        gas_used=used, gas_limit=gas_limit, max_fee_wei=max_fee, cap_wei=cap, gas_cost_wei=cost,
        expected_gross_wei=gross, net_wei=(gross - cost) if status else -cost,
        send_block=block, winner_block=winner, tx_index=int(receipt['transactionIndex'], 16))


def check():
    global _quiet
    cands = [(name, size * 10**18) for name in ROUTES for size in SIZES]
    gains = probe(cands)
    gross = max(gains)
    name, amount = cands[gains.index(gross)]
    if gross < MIN_INTEREST_WEI:
        _quiet += 1
        if _quiet % 20 == 1:     # one line every 10 minutes while nothing is there
            log('check', result='no_gain', best_wei=gross, best_route=name if gross else None)
        return
    _quiet = 0
    base_fee, max_fee = fees()
    if max_fee > MAX_FEE_CAP_WEI:
        log('opportunity_skip', reason='fee_cap', route=name, gross_wei=gross, base_fee=base_fee)
        return
    try:
        estimate = int(rpc('eth_estimateGas', call_params(name, amount, 1)), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', route=name, gross_wei=gross, error=str(e)[:200])
        return
    gas_limit = estimate * 12 // 10
    cap = gas_limit * max_fee                     # the most this send can cost
    cap_usd = cap / 1e18 * POL_REF_USD
    log('opportunity', route=name, amount_wei=amount, gross_wei=gross, cap_wei=cap, base_fee=base_fee,
        max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit)
    if gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='gas_limit_or_usd_cap', route=name, gas_limit=gas_limit, cap_usd=cap_usd)
        return
    if gross <= cap:                              # send only when expected gross > this send's gas cap
        log('opportunity_skip', reason='gross_not_above_gas_cap', route=name, gross_wei=gross, cap_wei=cap)
        return
    checked, err = gain_of(name, amount, cap, gas_limit)   # the exact call that would be signed
    if checked <= cap:
        log('simulate_revert', step='guard', route=name, gross_wei=gross, cap_wei=cap, error=err)
        return
    if MODE == 'paper':
        log('paper_sim', result='success', route=name, amount_wei=amount, gross_wei=checked, cap_wei=cap,
            gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=TIP_WEI)
    else:
        send_live(name, amount, checked, cap, max_fee, gas_limit)


def main():
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), poll_seconds=POLL_SECONDS, routes=list(ROUTES))
    while True:
        started = time.monotonic()
        try:
            check()
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(1800)
        except Exception as e:
            log('check_error', error=str(e)[:300])
        time.sleep(max(1, POLL_SECONDS - (time.monotonic() - started)))


if __name__ == '__main__':
    main()
