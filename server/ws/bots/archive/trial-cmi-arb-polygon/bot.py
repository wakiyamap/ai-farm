#!/usr/bin/env python3
"""trial: CMI SetToken on Polygon. The Set Protocol BasicIssuanceModule issues CMI for its three components (WETH,
WBTC, USDC.e) and redeems it back, for anyone, at the component amounts. CMI also trades against USDC.e on one small
QuickSwap V2 pair that nobody quotes, so when ETH / BTC move the pair price is left away from the component value.
One Morpho-flash-funded transaction through the StepArb executor closes the gap: issue + sell on the pair (pair
above the component value) or buy on the pair + redeem (pair below).
Timer bot: the gap opens by ETH / BTC price drift against a static pair, not by one event, so it looks every 120 s."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'polygon'

# Addresses: from the incumbent's traced take 0xb844cfd5... and each checked with a getter (README, "Addresses").
MORPHO = '0x1bF0c2541F820E775182832f06c0B7Fc27A25f67'    # Morpho Blue, flashLoan(token, assets, data); 1.0M WPOL
WPOL = '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270'
USDCE = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
WETH = '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619'
WBTC = '0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6'
CMI = '0x83c92e1a4a824cd42f94012b7b50aff372e4d25f'       # SetToken; getComponents() = WETH, WBTC, USDC.e
MODULE = '0x38E5462BBE6A72F79606c1A0007468aA4334A92b'    # BasicIssuanceModule (Controller 0x75fbbdea... getModules())
QUICK = '0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff'     # QuickSwap V2 router (pair USDC.e/CMI 0x8a1d216e...)
UNIV3 = '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'     # Uniswap V3 SwapRouter02
POOL_WETH = '0x45dda9cb7c25131df268515131f647d726f50608'  # USDC.e (token0) / WETH (token1) 0.05 pct
POOL_WBTC = '0xeef1a9507b3d505f0062f2be9453981255b503c8'  # WBTC (token0) / USDC.e (token1) 0.05 pct
POOL_WPOL = '0xa374094527e1673a86de625aa59517c5de346d32'  # WPOL (token0) / USDC.e (token1) 0.05 pct
V3_FEE = 500

# Selectors and topics from `cast sig` / `cast keccak` (scratch/trial-cmi-arb-polygon/setup.py, reads.py).
SEL_TAKE = '0x13b75307'      # take(address,address,uint256,(address,address,address,uint256,uint256,bytes)[],address[],uint256,bool)
SEL_PROBE = '0x8ad8bbaf'     # probe(bytes[])
SEL_V3_IN = '0x04e45aaf'     # exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))
SEL_V3_OUT = '0x5023b4df'    # exactOutputSingle((address,address,uint24,address,uint256,uint256,uint160))
SEL_V2_IN = '0x38ed1739'     # swapExactTokensForTokens(uint256,uint256,address[],address,uint256)
SEL_V2_OUT = '0x8803dbee'    # swapTokensForExactTokens(uint256,uint256,address[],address,uint256)
SEL_APPROVE = '0x095ea7b3'   # approve(address,uint256)
SEL_ISSUE = '0x6d78f47a'     # issue(address,uint256,address)
SEL_REDEEM = '0x5c833bfd'    # redeem(address,uint256,address)
SEL_UNITS = '0x7a4ffd03'     # getRequiredComponentUnitsForIssue(address,uint256)
SEL_SLOT0 = '0x3850c7bd'     # slot0()
TOPIC_ISSUED = '0xc07f1e2fe31c4d90eae81f76d263d7995aac043a99d6ee6de9c0506047f541c2'    # SetTokenIssued(address,address,address,address,uint256)
TOPIC_REDEEMED = '0x05f8aaada00823525432114f0e904c6f7c0198a5b8f113ee635ff81aaf9566ad'  # SetTokenRedeemed(address,address,address,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000f11a7'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000311'
EXEC = os.environ.get('EXECUTOR_ADDR_POLYGON') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_POLYGON or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

MAXU = (1 << 256) - 1
BIG = 1 << 255
Q192 = 1 << 192
DEADLINE = 0xffffffffff
# CMI quantities tried per route (1e18 = 1 CMI, about 111 USD). The pair holds about 6 CMI + 670 USDC.e; the
# incumbent's takes used 0.088 CMI (10 USDC.e).
SIZES = (15 * 10**15, 30 * 10**15, 45 * 10**15, 60 * 10**15, 100 * 10**15, 160 * 10**15, 250 * 10**15)
ROUTES = ('issue', 'redeem')
CLEAR = (USDCE, WETH, WBTC, CMI)
POLL = 120                        # seconds between looks (the gain stood 100-3,000+ blocks of 2 s above the send line)
PRICE_TTL = 1800                  # component units and the three pool prices only size the flash loan (5-10 pct spare)
SEND_MULT = 2                     # send line = 2 x gas cap (about 1.0-1.1 POL; the incumbent takes at 1.5-2.0 WPOL)
MIN_INTEREST_WEI = 10**17        # below 0.1 WPOL a take cannot cover its gas: no estimate, no log line
TIP_WEI = 30 * 10**9              # Polygon's minimum priority fee; never raised
MAX_FEE_CAP_WEI = 1500 * 10**9    # never sign above this
GAS_LIMIT_MAX = 2_400_000
POL_REF_USD = 0.15                # conservative (measured 0.072-0.074 USD on 2026-11-21)
MAX_TX_USD = 0.95
CU_CAP = 95_000
CU_COST = {'eth_call': 26, 'eth_getBlockByNumber': 20, 'eth_estimateGas': 20,
           'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10, 'eth_getLogs': 75}

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'cu.json'
_sizing = {'ts': 0}
_last_cap = {'ts': 0, 'cap': 0}
CAP_TTL = 1800


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


def step(target, token_in, spender, data, offset=MAXU, amount=0):
    return {'target': target, 'tokenIn': token_in or '0x' + '00' * 20,
            'spender': spender or '0x' + '00' * 20, 'amount': amount, 'offset': offset, 'data': data}


def v3_in(token_in, token_out, to):
    """Sell the executor's whole balance of token_in (the amount word is written by the executor)."""
    data = SEL_V3_IN + a(token_in) + a(token_out) + w(V3_FEE) + a(to) + w(0) + w(0) + w(0)
    return step(UNIV3, token_in, UNIV3, data, 4 + 4 * 32)


def v3_out(token_in, token_out, amount_out, to):
    """Buy exactly amount_out; the router may pull at most the executor's balance of token_in (the approval)."""
    data = SEL_V3_OUT + a(token_in) + a(token_out) + w(V3_FEE) + a(to) + w(amount_out) + w(BIG) + w(0)
    return step(UNIV3, token_in, UNIV3, data)


def v2_in(token_in, token_out, to):
    data = SEL_V2_IN + w(0) + w(0) + w(0xa0) + a(to) + w(DEADLINE) + w(2) + a(token_in) + a(token_out)
    return step(QUICK, token_in, QUICK, data, 4)


def v2_out(token_in, token_out, amount_out, to):
    data = SEL_V2_OUT + w(amount_out) + w(BIG) + w(0xa0) + a(to) + w(DEADLINE) + w(2) + a(token_in) + a(token_out)
    return step(QUICK, token_in, QUICK, data)


def approve_exact(token, spender, amount):
    """Approval of exactly what the module pulls in the next step (issue takes all of it: allowance ends at 0)."""
    return step(token, None, None, SEL_APPROVE + a(spender) + w(amount))


def component_amounts(units, qty):
    """BasicIssuanceModule.issue pulls preciseMulCeil(unit, quantity) of each component."""
    return [-(-u * qty // 10**18) for u in units]


def route_steps(name, qty, units, to):
    weth_amt, wbtc_amt, usdc_amt = component_amounts(units, qty)
    if name == 'issue':     # pair above component value: buy the components, issue CMI, sell it on the pair
        return [v3_in(WPOL, USDCE, to),
                v3_out(USDCE, WETH, weth_amt, to),
                v3_out(USDCE, WBTC, wbtc_amt, to),
                approve_exact(WETH, MODULE, weth_amt),
                approve_exact(WBTC, MODULE, wbtc_amt),
                approve_exact(USDCE, MODULE, usdc_amt),
                step(MODULE, None, None, SEL_ISSUE + a(CMI) + w(qty) + a(to)),
                v2_in(CMI, USDCE, to),
                v3_in(USDCE, WPOL, to)]
    if name == 'redeem':    # pair below component value: buy CMI on the pair, redeem, sell the components
        return [v3_in(WPOL, USDCE, to),
                v2_out(USDCE, CMI, qty, to),
                step(MODULE, None, None, SEL_REDEEM + a(CMI) + w(qty) + a(to)),
                v3_in(WETH, USDCE, to),
                v3_in(WBTC, USDCE, to),
                v3_in(USDCE, WPOL, to)]
    raise ValueError(name)


def enc_step(s):
    data = bytes.fromhex(s['data'].removeprefix('0x'))
    pad = (-len(data)) % 32
    return (a(s['target']) + a(s['tokenIn']) + a(s['spender']) + w(s['amount']) + w(s['offset'])
            + w(6 * 32) + w(len(data)) + data.hex() + '00' * pad)


def take_calldata(name, qty, flash, units, min_profit, executor):
    steps = [enc_step(s) for s in route_steps(name, qty, units, executor)]
    offs, pos = [], 32 * len(steps)
    for s in steps:
        offs.append(pos)
        pos += len(s) // 2
    steps_blob = w(len(steps)) + ''.join(w(o) for o in offs) + ''.join(steps)
    clear_blob = w(len(CLEAR)) + ''.join(a(t) for t in CLEAR)
    head = 7 * 32
    return (SEL_TAKE + a(MORPHO) + a(WPOL) + w(flash) + w(head) + w(head + len(steps_blob) // 2)
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


def view(to, data, block='latest'):
    return rpc('eth_call', [{'to': to, 'data': data}, block])


def sizing(block='latest', force=False):
    """Component units per 1 CMI and the three pool prices. Used for the exact issue amounts (units) and for the
    flash size (prices, with spare). Re-read every PRICE_TTL seconds and after any failed look."""
    if not force and block == 'latest' and time.time() - _sizing['ts'] < PRICE_TTL:
        return _sizing
    res = view(MODULE, SEL_UNITS + a(CMI) + w(10**18), block)
    ws = [res[2 + i:2 + i + 64] for i in range(0, len(res) - 2, 64)]
    n = int(ws[2], 16)
    comps = ['0x' + ws[3 + i][24:] for i in range(n)]
    if n != 3 or [c.lower() for c in comps] != [WETH.lower(), WBTC.lower(), USDCE.lower()]:
        raise RuntimeError(f'CMI components changed: {comps}')
    units = [int(ws[4 + n + i], 16) for i in range(n)]
    sq = {k: int(view(p, SEL_SLOT0, block)[2:66], 16) for k, p in
          (('weth', POOL_WETH), ('wbtc', POOL_WBTC), ('wpol', POOL_WPOL))}
    out = {'ts': time.time() if block == 'latest' else 0, 'units': units, 'sq': sq}
    if block == 'latest':
        _sizing.update(out)
    return out


def flash_for(name, qty, sz):
    """WPOL to borrow: the USDC.e value of the components of qty CMI at the pool prices, plus spare (the unused part
    only passes through the WPOL/USDC.e 0.05 pct pool and back)."""
    weth_amt, wbtc_amt, usdc_amt = component_amounts(sz['units'], qty)
    usdc = weth_amt * Q192 // sz['sq']['weth'] ** 2 + wbtc_amt * sz['sq']['wbtc'] ** 2 // Q192 + usdc_amt
    wpol = usdc * Q192 // sz['sq']['wpol'] ** 2
    return wpol * (106 if name == 'issue' else 112) // 100


def candidates(sz):
    return [(name, qty, flash_for(name, qty, sz)) for name in ROUTES for qty in SIZES]


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


def call_params(data, gas_limit=None, block='latest'):
    ex = executor()
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': ex, 'data': data}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx, block]
    if MODE == 'paper':
        params.append({ex: {'code': RUNTIME_FILE.read_text().strip()}})
    return params


def probe(cands, units, block='latest'):
    """Gains (WPOL wei) of every candidate in ONE eth_call; 0 = that take would revert."""
    ex = executor()
    data = probe_calldata([take_calldata(n, q, f, units, 1, ex) for n, q, f in cands])
    res = rpc('eth_call', call_params(data, None, block))
    words = [int(res[2 + i:2 + i + 64], 16) for i in range(0, len(res) - 2, 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(cands):
        raise RuntimeError('probe: unexpected return length')
    return gains


def gain_of(data, gas_limit=None, block='latest'):
    """Gain in WPOL wei of take() as an eth_call; 0 when it reverts (NoProfit or a failed step)."""
    ans = rpc('eth_call', call_params(data, gas_limit, block), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def fees(block='latest'):
    base_fee = int(rpc('eth_getBlockByNumber', [block, False])['baseFeePerGas'], 16)
    return base_fee, base_fee + base_fee // 4 + TIP_WEI


def last_cmi_take_block(block):
    """Block of the newest CMI issue / redeem near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': MODULE, 'fromBlock': hex(block - 60), 'toBlock': hex(block + 5),
                                'topics': [[TOPIC_ISSUED, TOPIC_REDEEMED], '0x' + a(CMI)]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(name, qty, flash, units, gross, cap, max_fee, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(name, qty, flash, units, cap, EXEC), 0, gas_limit,
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
        log('send_result', hash=tx_hash, result='unknown', route=name, qty=qty, expected_gross_wei=gross,
            cap_wei=cap, gas_limit=gas_limit, max_fee_wei=max_fee, gas_used=None, winner_block=None)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        winner = block if status else last_cmi_take_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', hash=tx_hash, result='won' if status else 'lost', route=name, qty=qty, flash_wei=flash,
        gas_used=used, gas_limit=gas_limit, max_fee_wei=max_fee, cap_wei=cap, gas_cost_wei=cost,
        expected_gross_wei=gross, net_wei=(gross - cost) if status else -cost,
        send_block=block, winner_block=winner, tx_index=int(receipt['transactionIndex'], 16))


def check(trigger='timer', block='latest'):
    """One look: one probe eth_call; more reads only when a gain above MIN_INTEREST_WEI stands."""
    sz = sizing(block)
    units = sz['units']
    cands = candidates(sz)
    gains = probe(cands, units, block)
    gross = max(gains)
    name, qty, flash = cands[gains.index(gross)]
    if gross < MIN_INTEREST_WEI:
        log('check', trigger=trigger, result='no_gain', best_wei=gross, best_route=name if gross else None,
            best_qty=qty if gross else None)
        return False
    # A gain often stands below the send line for hours. Against the last measured gas cap (kept CAP_TTL seconds)
    # such a look costs no further read.
    if block == 'latest' and time.time() - _last_cap['ts'] < CAP_TTL and gross * 10 < SEND_MULT * _last_cap['cap'] * 8:
        log('check', trigger=trigger, result='below_send_line', best_wei=gross, best_route=name, best_qty=qty,
            last_cap_wei=_last_cap['cap'])
        return True
    ex = executor()
    base_fee, max_fee = fees(block)
    if max_fee > MAX_FEE_CAP_WEI:
        log('opportunity_skip', trigger=trigger, reason='fee_cap', route=name, gross_wei=gross, base_fee=base_fee)
        return True
    try:
        estimate = int(rpc('eth_estimateGas', call_params(take_calldata(name, qty, flash, units, 1, ex), None, block)), 16)
    except Exception as e:
        log('simulate_revert', trigger=trigger, step='estimate', route=name, gross_wei=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 12 // 10
    cap = gas_limit * max_fee                     # the most this send can cost
    cap_usd = cap / 1e18 * POL_REF_USD
    if block == 'latest':
        _last_cap.update(ts=time.time(), cap=cap)
    log('opportunity', trigger=trigger, route=name, qty=qty, flash_wei=flash, gross_wei=gross, cap_wei=cap,
        base_fee=base_fee, max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit, all_gains=gains)
    if gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='gas_limit_or_usd_cap', route=name, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross <= SEND_MULT * cap:                  # send only when expected gross > twice this send's gas cap
        log('opportunity_skip', reason='gross_not_above_send_line', route=name, gross_wei=gross, cap_wei=cap,
            send_line_wei=SEND_MULT * cap)
        return True
    # the exact call that would be signed: minProfit = the gas cap
    checked, err = gain_of(take_calldata(name, qty, flash, units, cap, ex), gas_limit, block)
    if checked <= cap:
        log('simulate_revert', step='guard', route=name, gross_wei=gross, cap_wei=cap, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', trigger=trigger, route=name, qty=qty, flash_wei=flash, gross_wei=checked,
            cap_wei=cap, gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=TIP_WEI)
    else:
        send_live(name, qty, flash, units, checked, cap, max_fee, gas_limit)
    return True


def main():
    """Look every POLL seconds. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), routes=list(ROUTES), sizes=list(SIZES), poll_seconds=POLL)
    while True:
        try:
            check('timer')
            time.sleep(POLL)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            time.sleep(86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 5)   # to 00:00 UTC
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            _sizing['ts'] = 0                     # re-read units and prices at the next look
            time.sleep(POLL)


if __name__ == '__main__':
    main()
