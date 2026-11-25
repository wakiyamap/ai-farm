#!/usr/bin/env python3
"""trial: SPACE / xSPACE on Polygon. The XERC20Lockbox wraps SPACE into xSPACE and back 1:1 for anyone, while SPACE
trades against WPOL on a QuickSwap V2 pair and xSPACE against WPOL on a Uniswap V3 pool. When the two prices differ
by more than the fees, one Morpho-flash-funded transaction through the StepArb executor closes the gap.
Feed bot: it waits on the farm feed for a Swap on either pool (about 72 a day), looks again on a gap / 429 / 503 /
error, on a 5 min safety poll and on bounded follow-ups while a gain stands below its send line."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'polygon'
FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546').rstrip('/')   # farm-feed (wiki infra/feed.md)

# Addresses: from the incumbent's traced route, each checked with a getter (README, "Addresses").
MORPHO = '0x1bF0c2541F820E775182832f06c0B7Fc27A25f67'    # Morpho Blue, flashLoan(token, assets, data)
WPOL = '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270'
SPACE = '0xB53Ec4aCe420a62Cfb75aFdEba600D284777cd65'
XSPACE = '0x1D1498166DDCEeE616a6d99868e1E0677300056f'
LOCKBOX = '0x3267263E005F82A70867B567D4FF06D7E9C52ECf'   # XERC20Lockbox (verified): deposit / withdraw 1:1
QUICK = '0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff'     # QuickSwap V2 router (pair SPACE/WPOL 0xd6ab3f53...)
UNIV3 = '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'     # Uniswap V3 SwapRouter02 (pool xSPACE/WPOL 0.05 pct 0xdf6d2471...)
V3_FEE = 500

# Selectors, all from `cast sig` (scratch/trial-xspace-arb-polygon/sigs.py) and all seen in the incumbent's calldata.
SEL_TAKE = '0x13b75307'      # take(address,address,uint256,(address,address,address,uint256,uint256,bytes)[],address[],uint256,bool)
SEL_V3 = '0x04e45aaf'        # exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))
SEL_V2 = '0x38ed1739'        # swapExactTokensForTokens(uint256,uint256,address[],address,uint256)
SEL_DEPOSIT = '0xb6b55f25'   # deposit(uint256)
SEL_WITHDRAW = '0x2e1a7d4d'  # withdraw(uint256)
SEL_PROBE = '0x8ad8bbaf'     # probe(bytes[])
TOPIC_DEPOSIT = '0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'   # Deposit(address,uint256)
TOPIC_WITHDRAW = '0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364'  # Withdraw(address,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000f11a6'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000311'
EXEC = os.environ.get('EXECUTOR_ADDR_POLYGON') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_POLYGON or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

MAXU = (1 << 256) - 1
DEADLINE = 0xffffffffff
SIZES = (20, 60, 150, 400, 800)   # WPOL flash sizes tried per route; the incumbent's takes used 40-230 WPOL
ROUTES = ('wrap', 'unwrap')
CLEAR = (SPACE, XSPACE)
MIN_INTEREST_WEI = 10**17         # below 0.1 WPOL a take cannot cover its gas: no estimate, no log line
# Trigger: ONE feed /logs filter = the two pools, topic0 = the V3 and the V2 Swap event (measured 63 + 9.5 Swap logs a
# day over 2 days, 846-910 bytes each; scratch/trial-xspace-arb-polygon/swaps.py).
POOL_V3 = '0xdf6d24718662082e32a63647841cfc91699acd37'   # xSPACE/WPOL 0.05 pct (Uniswap V3 factory 0x1F98431c...)
PAIR_V2 = '0xd6ab3f53b1d71837fc1d66b856eeba7b87157e50'   # SPACE/WPOL (QuickSwap factory 0x57573714...)
SWAP_V3 = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
SWAP_V2 = '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'
SAFETY_POLL = 300                 # one probe() when nothing was looked at for this long (feed rule: 5-10 min)
FEED_TIMEOUT = 55                 # long-poll seconds
FEED_DOWN_POLL = 60               # while the feed answers 429 / 503 / errors: one state re-read at most this often
FOLLOW_UPS = (10, 30, 90)         # seconds after a look that left a gain standing below the send line
TIP_WEI = 30 * 10**9              # Polygon's minimum priority fee; never raised
MAX_FEE_CAP_WEI = 1500 * 10**9    # never sign above this
GAS_LIMIT_MAX = 900_000
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


def step(target, token_in, spender, data, offset, amount=0):
    return {'target': target, 'tokenIn': token_in or '0x' + '00' * 20,
            'spender': spender or '0x' + '00' * 20, 'amount': amount, 'offset': offset, 'data': data}


def v3_step(token_in, token_out, to):
    # exactInputSingle((tokenIn, tokenOut, fee, recipient, amountIn, amountOutMinimum, sqrtPriceLimitX96))
    data = SEL_V3 + a(token_in) + a(token_out) + w(V3_FEE) + a(to) + w(0) + w(0) + w(0)
    return step(UNIV3, token_in, UNIV3, data, 4 + 4 * 32)


def v2_step(token_in, token_out, to):
    data = SEL_V2 + w(0) + w(0) + w(0xa0) + a(to) + w(DEADLINE) + w(2) + a(token_in) + a(token_out)
    return step(QUICK, token_in, QUICK, data, 4)


def route_steps(name, to):
    if name == 'wrap':      # SPACE cheap on V2: WPOL -> SPACE (QuickSwap) -> deposit -> xSPACE -> WPOL (V3)
        return [v2_step(WPOL, SPACE, to),
                step(LOCKBOX, SPACE, LOCKBOX, SEL_DEPOSIT + w(0), 4),
                v3_step(XSPACE, WPOL, to)]
    if name == 'unwrap':    # xSPACE cheap on V3: WPOL -> xSPACE (V3) -> withdraw -> SPACE -> WPOL (QuickSwap)
        return [v3_step(WPOL, XSPACE, to),
                step(LOCKBOX, XSPACE, LOCKBOX, SEL_WITHDRAW + w(0), 4),   # XERC20.burn spends the lockbox's allowance
                v2_step(SPACE, WPOL, to)]
    raise ValueError(name)


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


def candidates():
    return [(name, size * 10**18) for name in ROUTES for size in SIZES]


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


def last_lockbox_block(block):
    """Block of the newest lockbox Deposit / Withdraw near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': LOCKBOX, 'fromBlock': hex(block - 60), 'toBlock': hex(block + 5),
                                'topics': [[TOPIC_DEPOSIT, TOPIC_WITHDRAW]]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


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
        winner = block if status else last_lockbox_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', hash=tx_hash, result='won' if status else 'lost', route=name, amount_wei=amount,
        gas_used=used, gas_limit=gas_limit, max_fee_wei=max_fee, cap_wei=cap, gas_cost_wei=cost,
        expected_gross_wei=gross, net_wei=(gross - cost) if status else -cost,
        send_block=block, winner_block=winner, tx_index=int(receipt['transactionIndex'], 16))


def check(trigger='manual'):
    """One look. Returns True when a gain was seen (taken or not): the caller schedules follow-up looks."""
    cands = candidates()
    gains = probe(cands)
    gross = max(gains)
    name, amount = cands[gains.index(gross)]
    if gross < MIN_INTEREST_WEI:
        log('check', trigger=trigger, result='no_gain', best_wei=gross, best_route=name if gross else None)
        return False
    base_fee, max_fee = fees()
    if max_fee > MAX_FEE_CAP_WEI:
        log('opportunity_skip', trigger=trigger, reason='fee_cap', route=name, gross_wei=gross, base_fee=base_fee)
        return True
    try:
        estimate = int(rpc('eth_estimateGas', call_params(name, amount, 1)), 16)
    except Exception as e:
        log('simulate_revert', trigger=trigger, step='estimate', route=name, gross_wei=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 12 // 10
    cap = gas_limit * max_fee                     # the most this send can cost
    cap_usd = cap / 1e18 * POL_REF_USD
    log('opportunity', trigger=trigger, route=name, amount_wei=amount, gross_wei=gross, cap_wei=cap, base_fee=base_fee,
        max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit)
    if gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='gas_limit_or_usd_cap', route=name, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross <= cap:                              # send only when expected gross > this send's gas cap
        log('opportunity_skip', reason='gross_not_above_gas_cap', route=name, gross_wei=gross, cap_wei=cap)
        return True
    checked, err = gain_of(name, amount, cap, gas_limit)   # the exact call that would be signed
    if checked <= cap:
        log('simulate_revert', step='guard', route=name, gross_wei=gross, cap_wei=cap, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', trigger=trigger, route=name, amount_wei=amount, gross_wei=checked,
            cap_wei=cap, gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=TIP_WEI)
    else:
        send_live(name, amount, checked, cap, max_fee, gas_limit)
    return True                                   # look again: part of the gap may be left, or the send lost


def feed_wait(cursor, timeout):
    """Long-poll the farm feed for Swap on the two pools (one filter). Returns the feed's JSON ({'cursor', 'logs'} plus
    'timeout' or 'gap'). HTTP 429 / 503 and connection errors raise (the caller re-reads state)."""
    q = {'address': f'{POOL_V3},{PAIR_V2}', 'topic0': f'{SWAP_V3},{SWAP_V2}', 'timeout': str(int(timeout))}
    if cursor:
        q['after'] = cursor
    url = f'{FEED}/logs/{CHAIN}?' + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=timeout + 15) as resp:
        return json.load(resp)


def look(s, trigger):
    """check() plus the follow-up schedule. A follow-up look arms nothing new."""
    s['last_check'] = time.time()
    standing = check(trigger)
    if trigger != 'follow_up':
        s['follow_ups'] = [time.time() + d for d in FOLLOW_UPS] if standing else []


def main():
    """Wait on the feed; look on an event, on a gap / removed log / feed error (state re-read), on the safety poll and
    on the bounded follow-ups. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    s = {'feed_cursor': None, 'follow_ups': [], 'last_check': 0}
    log('start', mode=MODE, executor=executor(), routes=list(ROUTES), sizes=list(SIZES), trigger='feed Swap',
        feed_address=[POOL_V3, PAIR_V2], feed_topic0=[SWAP_V3, SWAP_V2], safety_poll_seconds=SAFETY_POLL,
        follow_ups=list(FOLLOW_UPS))
    feed_down_until = 0
    while True:
        try:
            now = time.time()
            ups = s['follow_ups']
            if ups and now >= ups[0]:
                s['follow_ups'] = ups[1:]
                look(s, 'follow_up')
            elif now - s['last_check'] >= SAFETY_POLL:
                look(s, 'safety_poll' if s['last_check'] else 'start')
            elif now < feed_down_until:
                time.sleep(min(feed_down_until - now, 5))
            else:
                due = min([s['last_check'] + SAFETY_POLL] + ups[:1])
                try:
                    result = feed_wait(s['feed_cursor'], max(1, min(FEED_TIMEOUT, due - now)))
                except (urllib.error.URLError, OSError, ValueError) as e:
                    # 429 (filter slots or CU cap) / 503 / connection error: something may have been missed. Re-read
                    # state once now, then leave the feed alone for FEED_DOWN_POLL seconds.
                    log('feed_error', error=str(e)[:180])
                    feed_down_until = time.time() + FEED_DOWN_POLL
                    look(s, 'feed_error')
                    continue
                first = s['feed_cursor'] is None
                s['feed_cursor'] = result.get('cursor', s['feed_cursor'])
                logs = result.get('logs') or []
                if result.get('gap') or any(x.get('removed') for x in logs):
                    log('feed_gap', gap=bool(result.get('gap')), removed=sum(1 for x in logs if x.get('removed')))
                    look(s, 'feed_gap')
                elif logs:
                    log('feed', events=len(logs), blocks=sorted({int(x['blockNumber'], 16) for x in logs}),
                        txs=sorted({x['transactionHash'] for x in logs})[:4],
                        block_ts=[x.get('blockTimestamp') for x in logs][:4])
                    look(s, 'feed')
                elif first:
                    log('feed_subscribed', cursor=s['feed_cursor'])
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            s['follow_ups'] = []
            now = datetime.datetime.now(datetime.timezone.utc)
            time.sleep(86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 5)   # to 00:00 UTC
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            s['last_check'] = time.time()
            time.sleep(5)


if __name__ == '__main__':
    main()
