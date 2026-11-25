#!/usr/bin/env python3
"""trial: HEFE / aHEFE on Avalanche. aHEFE (0x4c726f61...) is a BIFKN314 token: the token contract is its own AVAX
pool (swapNativeToToken / swapTokenToNative). The public BIFKN314Wrapper (0xc6346fe9...) converts aHEFE <-> HEFE 1:1
for anyone (wrap / unwrap, no fee). HEFE (0x18e3605b...) trades on the Trader Joe V1 pair HEFE / WAVAX 0xe11e871d....
When a trade moves one pool more than the fees away from the other, one transaction through the WrapPairArb executor
closes the gap:
  unwrap direction (aHEFE cheap): flash swap WAVAX out of the pair -> buy aHEFE on the 314 pool -> unwrap -> repay the
    pair in HEFE -> sell the HEFE left on the pair -> pay the bot wallet in AVAX;
  wrap direction (HEFE cheap): flash swap HEFE out of the pair -> wrap -> sell aHEFE on the 314 pool -> repay the pair in
    WAVAX -> pay the bot wallet in AVAX.
The executor reverts unless the wallet is paid at least minProfit.
Feed bot: it waits on the farm feed for a Sync on the pair or a Swap on the 314 pool (ONE filter, two addresses, about
34 logs a day), then does ONE eth_call of the executor's probe() (a grid of sizes, both directions); it looks again on
a gap / 429 / 503 / connection error, on a 600 s safety poll and on a few follow-ups while a gain stands."""
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
CHAIN = 'avalanche'

# Addresses: the receipts of incumbent takes 0xa5912ce2c8cdf35b68962d8e4cb62dc87120d94d2506a85fcf0a0aa3e00bea2f and
# 0xe1e8fbbf59ff29b18d5378f9615253e94cd184c9d40045333747b53940dc8ea9; originalToken() / wrappedToken() of the wrapper,
# token0() / token1() / factory() of the pair and the verified sources (routescan) read on 2026-11-22
# (scratch/trial-hefe-wrap-avalanche/state.py, state.json).
A314 = '0x4c726f6159a883e94b87984d827453f6f5955098'        # aHEFE, BIFKN314 token = its own AVAX pool
WRAPPER = '0xc6346fe9f72c7ac09710914e98895b9bfba3bfd4'     # BIFKN314Wrapper: wrap(uint256) / unwrap(uint256), 1:1
HEFE = '0x18e3605b13f10016901eac609b9e188cf7c18973'        # the wrapper's originalToken, 1 pct tax into / out of the pair
PAIR = '0xe11e871d312cc9bae9eb24c7bdc2031f8453bf44'        # Trader Joe V1 HEFE (token0) / WAVAX (token1), 0.3 pct
WAVAX = '0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7'
FEE1000 = 997
TAX_PERMILLE = 10                                          # HEFE.tax() = 10 (per 1000)
# sizes probed each look: unwrap direction = WAVAX borrowed (0.05 x 1.4^k), wrap direction = HEFE borrowed
# (1,000 x 1.4^k), k = 0..13 (the 314 pool holds about 53 AVAX; incumbents moved 1.1 - 1.35 AVAX per take)
SIZES_UNWRAP = [int(5 * 10**16 * 1.4**k) for k in range(14)]
SIZES_WRAP = [int(1000 * 10**18 * 1.4**k) for k in range(14)]
CANDIDATES = [(True, s) for s in SIZES_UNWRAP] + [(False, s) for s in SIZES_WRAP]

# Selectors and topics from `cast sig` / `cast keccak` (checked again by scratch/trial-hefe-wrap-avalanche/proof.py).
SEL_TAKE = '0x867f1597'    # take((address,address,address,address,address,bool,uint256,uint256,uint256,uint256))
SEL_PROBE = '0xee8812e2'   # probe((...)[])
TOPIC_SYNC = '0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'      # Sync(uint112,uint112) (pair)
TOPIC_SWAP314 = '0xd44b536c8222cd875ef4b7f421435c474a3e1035e29c64e5f039af6944de4bea'   # Swap(address,uint256,uint256,uint256,uint256,bool) (314 pool)
TOPIC_WRAP = '0xb61d00fdfee32467c7d81db64c811ae60c104c346debf36a14afe84b8fce59e5'      # Wrap(address,uint256)
TOPIC_UNWRAP = '0x5dd085b6070b4cae004f84daafd199fd55b0bdfa11c3a802baffe89c2419d8c2'    # Unwrap(address,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000f11aa'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_AVALANCHE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_AVALANCHE or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546').rstrip('/')   # farm-feed (wiki infra/feed.md)
FEED_ADDRESSES = [PAIR, A314]      # ONE filter: Sync on the pair (32 a day) or Swap on the 314 pool (1.5 a day)
FEED_TOPICS = [TOPIC_SYNC, TOPIC_SWAP314]
SAFETY_POLL = 600                  # one probe() when nothing was looked at for this long (feed rule: 5-10 min)
FEED_TIMEOUT = 55                  # long-poll seconds
FEED_DOWN_POLL = 60                # while the feed answers 429 / 503 / errors: one state re-read at most this often
FOLLOW_UPS = (4, 15, 45)           # seconds after a look that saw a gain: part may be left, or the send lost
MIN_INTEREST_WEI = 3 * 10**15      # 0.003 AVAX (about 0.02 USD): below this no take covers its gas
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send when gross > 1.3 x the send's cost cap
TIP_SHARE_DEN = 10                 # priority fee: at most 1/10 of gross spread over the gas limit ...
TIP_MAX_WEI = 50 * 10**9           # ... and never above 50 gwei
TIP_MIN_WEI = 1 * 10**9
MAX_FEE_CAP_WEI = 200 * 10**9      # never sign above 200 gwei
GAS_LIMIT_MAX = 900_000
AVAX_REF_USD = 20.0                # deliberately high AVAX price for the USD cap (AVAX was 6.59 USD on 2026-11-22)
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


def take_tuple(unwrap_dir, amount, min_profit):
    """ABI encoding of one Take struct (static: 10 words)."""
    return (a(A314) + a(WRAPPER) + a(HEFE) + a(PAIR) + a(WAVAX) + w(1 if unwrap_dir else 0) + w(amount) + w(FEE1000)
            + w(TAX_PERMILLE) + w(min_profit))


def take_calldata(unwrap_dir, amount, min_profit):
    return SEL_TAKE + take_tuple(unwrap_dir, amount, min_profit)


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
    """Gains (wei of AVAX) of each candidate on chain in ONE eth_call; 0 = that take would revert."""
    res = rpc('eth_call', call_params(probe_calldata(cands), None, block)).removeprefix('0x')
    words = [int(res[i:i + 64], 16) for i in range(0, len(res), 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(cands):
        raise RuntimeError('probe: unexpected return length')
    return gains


def gain_of(unwrap_dir, amount, min_profit, gas_limit=None):
    """Return value of the exact take() as an eth_call; 0 when it reverts."""
    ans = rpc('eth_call', call_params(take_calldata(unwrap_dir, amount, min_profit), gas_limit), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def last_wrapper_block(block):
    """Block of the newest Wrap / Unwrap on the wrapper near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': WRAPPER, 'fromBlock': hex(block - 300), 'toBlock': hex(block + 5),
                                'topics': [[TOPIC_WRAP, TOPIC_UNWRAP]]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(unwrap_dir, amount, gross, cap, max_fee, tip, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(unwrap_dir, amount, cap), 0, gas_limit, max_fee,
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
    common = dict(hash=tx_hash, unwrap_dir=unwrap_dir, amount_wei=amount, expected_gross_wei=gross, cap_wei=cap,
                  gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        winner = block if status else last_wrapper_block(block)
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
    unwrap_dir, amount = CANDIDATES[gains.index(gross)]
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(take_calldata(unwrap_dir, amount, 1))), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', unwrap_dir=unwrap_dir, amount_wei=amount, gross_wei=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 13 // 10
    tip = max(TIP_MIN_WEI, min(TIP_MAX_WEI, gross // TIP_SHARE_DEN // gas_limit))
    max_fee = base_fee + base_fee // 4 + tip
    cap = gas_limit * max_fee                          # the most this send can cost (maxFeePerGas x gasLimit)
    cap_usd = cap / 1e18 * AVAX_REF_USD
    log('opportunity', unwrap_dir=unwrap_dir, amount_wei=amount, gross_wei=gross, gains_wei=gains, cap_wei=cap,
        base_fee=base_fee, tip_wei=tip, max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit,
        cap_usd=round(cap_usd, 4))
    if max_fee > MAX_FEE_CAP_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', max_fee_wei=max_fee, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross * SEND_MULT_DEN <= cap * SEND_MULT_NUM:   # send only when expected gross > 1.3 x this send's cost cap
        log('opportunity_skip', reason='gross_below_send_line', gross_wei=gross, cap_wei=cap)
        return True
    checked, err = gain_of(unwrap_dir, amount, cap, gas_limit)   # the exact call that would be signed (minProfit = cap)
    if checked <= cap:
        log('simulate_revert', step='guard', unwrap_dir=unwrap_dir, amount_wei=amount, gross_wei=gross, cap_wei=cap, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', unwrap_dir=unwrap_dir, amount_wei=amount, gross_wei=checked, cap_wei=cap,
            gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    else:
        send_live(unwrap_dir, amount, checked, cap, max_fee, tip, gas_limit)
    return True


def feed_wait(cursor, timeout):
    """Long-poll the farm feed for Sync on the pair / Swap on the 314 pool (one filter). Returns the feed's JSON
    ({'cursor', 'logs'} plus 'timeout' or 'gap'). HTTP 429 / 503 and connection errors raise (the caller re-reads)."""
    q = {'address': ','.join(FEED_ADDRESSES), 'topic0': ','.join(FEED_TOPICS), 'timeout': str(int(timeout))}
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
    log('start', mode=MODE, executor=executor(), pair=PAIR, token314=A314, wrapper=WRAPPER, candidates=len(CANDIDATES),
        trigger='feed Sync / Swap', feed_address=FEED_ADDRESSES, feed_topic0=FEED_TOPICS,
        safety_poll_seconds=SAFETY_POLL, follow_ups=list(FOLLOW_UPS))
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
