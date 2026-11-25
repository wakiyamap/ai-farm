#!/usr/bin/env python3
"""trial: dQUICK (QuickSwap DragonLair over the old QUICK token, 0xf28164a4...) against old QUICK (0x831753dd...) on
Polygon. The DragonLair is a "bar" vault: enter(uint256) / leave(uint256) convert at QUICK held / dQUICK supply, no fee,
no delay, open to anyone. dQUICK also trades in the QuickSwap V2 pair dQUICK / QUICK 0xb187ad7b.... When holders sell
dQUICK into the pair its price falls under the vault rate; one transaction through the LairPairArb executor then does:
flash swap dQUICK out of the pair -> leave() -> repay the pair in QUICK -> sell the QUICK left on the QUICK / WPOL V2
pair -> unwrap -> pay the bot wallet in POL. The other direction (pair price above the rate: borrow QUICK, enter(),
repay dQUICK, leave the rest) is covered too. The executor reverts unless the wallet is paid at least minProfit.
Feed bot: it waits on the farm feed for a Sync on the dQUICK / QUICK pair (about 8 logs a day), then does ONE eth_call
of the executor's probe() (a grid of sizes, both directions); it looks again on a gap / 429 / 503 / connection error,
on a 300 s safety poll (the vault rate can also move without a pair event) and on a few follow-ups while a gain stands."""
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
RELAY = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545').rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'polygon'

# Addresses: the receipts of incumbent takes 0x865eabdb72b7aef83d7b19913f6ce7577bfc244ca13506eb81e94676349acce8 and
# 0x74c792a125a73b36cbc7388e6cd0815d752de41bfebf77b61f2f425a1bb4b749 (pair, vault, QUICK); the sale pair is
# QuickSwap V2 factory 0x5757371414417b8C6CAad45bAeF941aBc7d3Ab32 getPair(QUICK, WPOL); token0() / factory() of both
# pairs and quick() of the vault read on chain (scratch/trial-quick-convert-polygon/pools.py, lair.py).
PAIR = '0xb187ad7bb9933bc4152f3da30e18600352d65792'        # QuickSwap V2 old QUICK (token0) / dQUICK (token1)
LAIR = '0xf28164a485b0b2c90639e47b0f377b4a438a16b1'        # DragonLair = dQUICK; enter(uint256) / leave(uint256)
QUICK = '0x831753dd7087cac61ab5644b308642cc1c33dc13'       # old QUICK, the vault's base token
SALE_PAIR = '0x019ba0325f1988213d448b3472fa1cf8d07618d7'   # QuickSwap V2 old QUICK / WPOL (2,441 QUICK / 296k WPOL)
WPOL = '0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270'
FEE1000 = 997
# sizes probed each look: leave direction = dQUICK borrowed (0.01 x 1.3^k), enter direction = QUICK borrowed
# (0.02 x 1.3^k), k = 0..21 (the pair holds about 12.6 dQUICK / 21.9 QUICK; incumbents took 0.14 - 1.1 dQUICK)
SIZES_LEAVE = [int(10**16 * 1.3**k) for k in range(22)]
SIZES_ENTER = [int(2 * 10**16 * 1.3**k) for k in range(22)]
CANDIDATES = [(True, s) for s in SIZES_LEAVE] + [(False, s) for s in SIZES_ENTER]

# Selectors and topics from `cast sig` / `cast keccak` (checked again by scratch/trial-dquick-lair-polygon/proof.py).
SEL_TAKE = '0x71c6fd31'    # take((address,address,address,address,address,bool,uint256,uint256,uint256))
SEL_PROBE = '0x49ab2d1f'   # probe((...)[])
TOPIC_SYNC = '0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'   # Sync(uint112,uint112)
TOPIC_SWAP = '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'   # Swap(address,uint256,uint256,uint256,uint256,address)

PAPER_EXEC = '0x00000000000000000000000000000000000f11a9'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_POLYGON') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_POLYGON or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546').rstrip('/')   # farm-feed (wiki infra/feed.md)
FEED_ADDRESSES = [PAIR]            # ONE filter: Sync on the dQUICK / QUICK pair (44 pair logs in 5.2 days)
SAFETY_POLL = 300                  # one probe() when nothing was looked at for this long (feed rule: 5-10 min)
FEED_TIMEOUT = 55                  # long-poll seconds
FEED_DOWN_POLL = 60                # while the feed answers 429 / 503 / errors: one state re-read at most this often
FOLLOW_UPS = (4, 15, 45)           # seconds after a look that saw a gain: part may be left, or the send lost
MIN_INTEREST_WEI = 5 * 10**16      # 0.05 POL (about 0.004 USD): below this no take covers its gas
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send when gross > 1.3 x the send's cost cap
TIP_SHARE_DEN = 10                 # priority fee: at most 1/10 of gross spread over the gas limit ...
TIP_MAX_WEI = 300 * 10**9          # ... and never above 300 gwei
TIP_MIN_WEI = 30 * 10**9           # Polygon validators' floor is 25 gwei
MAX_FEE_CAP_WEI = 3000 * 10**9     # never sign above 3,000 gwei
GAS_LIMIT_MAX = 900_000
POL_REF_USD = 0.25                 # deliberately high POL price for the USD cap (POL was about 0.075 USD on 2026-11-22)
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


def w(n):
    return format(n, '064x')


def a(addr):
    return addr.lower().removeprefix('0x').zfill(64)


def take_tuple(leave_dir, amount, min_profit):
    """ABI encoding of one Take struct (static: 9 words)."""
    return (a(PAIR) + a(LAIR) + a(QUICK) + a(SALE_PAIR) + a(WPOL) + w(1 if leave_dir else 0) + w(amount) + w(FEE1000)
            + w(min_profit))


def take_calldata(leave_dir, amount, min_profit):
    return SEL_TAKE + take_tuple(leave_dir, amount, min_profit)


def probe_calldata(cands):
    return SEL_PROBE + w(32) + w(len(cands)) + ''.join(take_tuple(d, s, 1) for d, s in cands)


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


def probe(cands, block='latest'):
    """Gains (wei of POL) of each candidate on chain in ONE eth_call; 0 = that take would revert."""
    res = rpc('eth_call', call_params(probe_calldata(cands), None, block)).removeprefix('0x')
    words = [int(res[i:i + 64], 16) for i in range(0, len(res), 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(cands):
        raise RuntimeError('probe: unexpected return length')
    return gains


def gain_of(leave_dir, amount, min_profit, gas_limit=None):
    """Return value of the exact take() as an eth_call; 0 when it reverts."""
    ans = rpc('eth_call', call_params(take_calldata(leave_dir, amount, min_profit), gas_limit), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def last_pair_swap_block(block):
    """Block of the newest swap on the pair near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': PAIR, 'fromBlock': hex(block - 300), 'toBlock': hex(block + 5), 'topics': [TOPIC_SWAP]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(leave_dir, amount, gross, cap, max_fee, tip, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(leave_dir, amount, cap), 0, gas_limit, max_fee,
                                max_priority_fee_per_gas=tip)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', reply=reply)
        return
    receipt = None
    for _ in range(20):
        time.sleep(2)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    common = dict(hash=tx_hash, leave_dir=leave_dir, amount_wei=amount, expected_gross_wei=gross, cap_wei=cap,
                  gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        winner = block if status else last_pair_swap_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        net_wei=(gross - cost) if status else -cost, send_block=block, winner_block=winner,
        tx_index=int(receipt['transactionIndex'], 16), **common)


def check():
    """One look: 1 eth_call when nothing is open. Returns True when a gain above MIN_INTEREST was seen."""
    gains = probe(CANDIDATES)
    gross = max(gains)
    if gross < MIN_INTEREST_WEI:
        return False
    leave_dir, amount = CANDIDATES[gains.index(gross)]
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(take_calldata(leave_dir, amount, 1))), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', leave_dir=leave_dir, amount_wei=amount, gross_wei=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 13 // 10
    tip = max(TIP_MIN_WEI, min(TIP_MAX_WEI, gross // TIP_SHARE_DEN // gas_limit))
    max_fee = base_fee + base_fee // 4 + tip
    cap = gas_limit * max_fee                          # the most this send can cost (maxFeePerGas x gasLimit)
    cap_usd = cap / 1e18 * POL_REF_USD
    log('opportunity', leave_dir=leave_dir, amount_wei=amount, gross_wei=gross, gains_wei=gains, cap_wei=cap,
        base_fee=base_fee, tip_wei=tip, max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit,
        cap_usd=round(cap_usd, 4))
    if max_fee > MAX_FEE_CAP_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', max_fee_wei=max_fee, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross * SEND_MULT_DEN <= cap * SEND_MULT_NUM:   # send only when expected gross > 1.3 x this send's cost cap
        log('opportunity_skip', reason='gross_below_send_line', gross_wei=gross, cap_wei=cap)
        return True
    checked, err = gain_of(leave_dir, amount, cap, gas_limit)   # the exact call that would be signed (minProfit = cap)
    if checked <= cap:
        log('simulate_revert', step='guard', leave_dir=leave_dir, amount_wei=amount, gross_wei=gross, cap_wei=cap, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', leave_dir=leave_dir, amount_wei=amount, gross_wei=checked, cap_wei=cap,
            gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    else:
        send_live(leave_dir, amount, checked, cap, max_fee, tip, gas_limit)
    return True


def feed_wait(cursor, timeout):
    """Long-poll the farm feed for Sync on the dQUICK / QUICK pair (one filter). Returns the feed's JSON ({'cursor',
    'logs'} plus 'timeout' or 'gap'). HTTP 429 / 503 and connection errors raise (the caller re-reads state)."""
    q = {'address': ','.join(FEED_ADDRESSES), 'topic0': TOPIC_SYNC, 'timeout': str(int(timeout))}
    if cursor:
        q['after'] = cursor
    url = f'{FEED}/logs/{CHAIN}?' + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=timeout + 15) as resp:
        return json.load(resp)


def look(s, trigger):
    """check() plus the follow-up schedule. A follow-up look arms nothing new."""
    s['last_check'] = time.time()
    s['looks'] += 1
    standing = check()
    if standing:
        log('look', trigger=trigger, standing=True)
    elif s['looks'] % 50 == 1:
        log('heartbeat', looks=s['looks'], trigger=trigger)
    if trigger != 'follow_up':
        s['follow_ups'] = [time.time() + d for d in FOLLOW_UPS] if standing else []


def main():
    """Wait on the feed; look on an event, on a gap / removed log / feed error (state re-read), on the safety poll and
    on the bounded follow-ups. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    s = {'feed_cursor': None, 'follow_ups': [], 'last_check': 0, 'looks': 0}
    log('start', mode=MODE, executor=executor(), pair=PAIR, lair=LAIR, candidates=len(CANDIDATES), trigger='feed Sync',
        feed_address=FEED_ADDRESSES, feed_topic0=TOPIC_SYNC, safety_poll_seconds=SAFETY_POLL, follow_ups=list(FOLLOW_UPS))
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
