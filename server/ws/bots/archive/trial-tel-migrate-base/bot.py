#!/usr/bin/env python3
"""trial: old TEL (0x09be1692..., 2 decimals) against new TEL / TelcoinV3 (0x7e13b430..., 18 decimals) on Base.
Telcoin's TokenMigration 0x2703e00c... has a public migrate(): it escrows the caller's whole old-TEL balance and mints
the same amount of new TEL (x 1e16 for the decimals), no fee, until migrationExpiry (2027-09-24). Both tokens trade
against native ETH in Uniswap v4 pools (fee 0.3 pct each). The migration is one-way, so only "old TEL cheaper than new
TEL by more than 0.6 pct" can be closed: one transaction through the V4MigrateArb executor does, inside one PoolManager
unlock (v4 flash accounting, no principal): ETH -> old TEL, migrate(), new TEL -> ETH, take the difference, pay the bot
wallet. The executor reverts unless the wallet is paid at least minProfit. Feed bot: it waits on the farm feed for a
Transfer of old TEL or new TEL (any trade of either moves one of the two pools), then does ONE eth_call of the
executor's probe() (a grid of sizes); it looks again on a gap / 429 / 503 / connection error, on a 300 s safety poll
and on a few follow-ups while a gain stands."""
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
CHAIN = 'base'

# Addresses: all from the trace of incumbent take 0x72df13d1a0676ad22f5284d3031798e0dea8fb2c5f175d21196050dfedc4f983
# (scratch/r1805/trace-0x72df13d1.json, pool keys decoded by scratch/rec73/dec.py); oldToken() / telcoinV3() read from
# the migrator on chain (scratch/rec73/census.py); migrator source verified (scratch/rec73/src-mig).
MANAGER = '0x498581ff718922c3f8e6a244956af099b2652b2b'     # Uniswap v4 PoolManager on Base
MIGRATOR = '0x2703e00cae30a7707e4d18c38f8cb6a4a40c2703'    # Telcoin TokenMigration: migrate() 0x8fd3ab80, public
OLD = '0x09be1692ca16e06f536f0038ff11d1da8524adb1'         # old TEL, 2 decimals
NEW = '0x7e13b43065380acdec1c2d138c579cbbbafa0731'         # TelcoinV3, 18 decimals
ZERO = '0x0000000000000000000000000000000000000000'
OLD_KEY = (ZERO, OLD, 3000, 60, '0x23ab2e6d4ab0c5f872567098671f1ffb46fd2500')   # ETH / old TEL, TELxIncentiveHook
NEW_KEY = (ZERO, NEW, 3000, 60, ZERO)                                           # ETH / new TEL, no hook
# ETH sizes probed each look: 0.002 x 1.6^k, k = 0..12 (0.002 .. 0.56 ETH; the incumbent's best take used 0.0884)
SIZES = [int(2 * 10**15 * 1.6**k) for k in range(13)]

# Selectors from `cast sig` (checked again by scratch/trial-tel-migrate-base/proof.py).
SEL_TAKE = '0x39352cb0'    # take((address,address,(address,address,uint24,int24,address),(address,address,uint24,int24,address),uint256,uint256))
SEL_PROBE = '0x4ff7fcb0'   # probe((...)[])
TOPIC_MIGRATED = '0x2558d4091fc8e966ac64668ecbe596974579c9f0e5b2e11d94d1469934ab5fd8'   # TokensMigrated(address,uint256), cast keccak

PAPER_EXEC = '0x00000000000000000000000000000000000f11a9'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546').rstrip('/')   # farm-feed (wiki infra/feed.md)
# Trigger: ONE feed /logs filter = the two TEL tokens, topic0 = ERC-20 Transfer (cast keccak
# "Transfer(address,address,uint256)"). The v4 PoolManager's Swap event is NOT subscribed (one emitter for every v4
# pool on Base: busy). Log counts per day: README.
FEED_ADDRESSES = [OLD, NEW]
TOPIC_TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
MIN_LOOK_GAP = 3                   # seconds between two feed-triggered looks (a burst of transfers = one look)
SAFETY_POLL = 300                  # one probe() when nothing was looked at for this long (feed rule: 5-10 min)
FEED_TIMEOUT = 55                  # long-poll seconds
FEED_DOWN_POLL = 60                # while the feed answers 429 / 503 / errors: one state re-read at most this often
FOLLOW_UPS = (4, 15, 45)           # seconds after a look that saw a gain: part may be left, or the send lost
MIN_INTEREST_WEI = 10**13          # 0.00001 ETH (about 0.02 USD): below this no take covers its gas
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send when gross > 1.3 x the send's cost cap
TIP_SHARE_DEN = 10                 # priority fee: at most 1/10 of gross spread over the gas limit ...
TIP_MAX_WEI = 10**8                # ... and never above 0.1 gwei
TIP_MIN_WEI = 10**6
MAX_FEE_CAP_WEI = 2 * 10**8        # never sign above 0.2 gwei
GAS_LIMIT_MAX = 2_500_000
L1_FEE_ALLOW_WEI = 10**12          # allowance for the OP Stack L1 data fee (measured about 4e9 wei for such a tx)
ETH_REF_USD = 4000.0               # deliberately high ETH price for the USD cap (ETH was 1,704.5 USD on 2026-11-22)
WALLET_MAX_USD = 0.95              # live: no send while the wallet's native balance is worth this much or more
# Chainlink ETH / USD on Base: description() answered 'ETH / USD', latestAnswer() 1,704.5 (scratch/trial-tel-migrate-base/stats.py)
ETH_USD_FEED = '0x71041dddad3595f9ced3dccfbe3d1f4b0a16bb70'
MAX_TX_USD = 0.95
CU_CAP = 95_000
CU_COST = {'eth_call': 26, 'eth_getBlockByNumber': 20, 'eth_estimateGas': 20,
           'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10, 'eth_getLogs': 75, 'eth_getBalance': 20}

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


def key_words(k):
    return a(k[0]) + a(k[1]) + w(k[2]) + w(k[3]) + a(k[4])


def take_tuple(amount, min_profit):
    """ABI encoding of one Take struct (static: 14 words)."""
    return a(MANAGER) + a(MIGRATOR) + key_words(OLD_KEY) + key_words(NEW_KEY) + w(amount) + w(min_profit)


def take_calldata(amount, min_profit):
    return SEL_TAKE + take_tuple(amount, min_profit)


def probe_calldata(sizes):
    return SEL_PROBE + w(32) + w(len(sizes)) + ''.join(take_tuple(s, 1) for s in sizes)


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


def wallet_usd():
    """Live only: the bot wallet's native balance in USD at the Chainlink ETH / USD answer on Base."""
    balance = int(rpc('eth_getBalance', [owner(), 'latest']), 16)
    price = int(rpc('eth_call', [{'to': ETH_USD_FEED, 'data': '0x50d25bcd'}, 'latest']), 16) / 1e8   # latestAnswer()
    if not 300 < price < 20000:
        raise RuntimeError(f'ETH/USD feed answer out of range: {price}')
    return balance * price / 1e18


def call_params(data, gas_limit=None, block='latest'):
    ex = executor()
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': ex, 'data': data}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx, block]
    if MODE == 'paper':
        params.append({ex: {'code': RUNTIME_FILE.read_text().strip()}})
    return params


def probe(sizes, block='latest'):
    """Gains (wei of ETH) of each size on chain in ONE eth_call; 0 = that take would revert."""
    res = rpc('eth_call', call_params(probe_calldata(sizes), None, block)).removeprefix('0x')
    words = [int(res[i:i + 64], 16) for i in range(0, len(res), 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(sizes):
        raise RuntimeError('probe: unexpected return length')
    return gains


def gain_of(amount, min_profit, gas_limit=None):
    """Return value of the exact take() as an eth_call; 0 when it reverts."""
    ans = rpc('eth_call', call_params(take_calldata(amount, min_profit), gas_limit), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def last_migration_block(block):
    """Block of the newest migration near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': MIGRATOR, 'fromBlock': hex(block - 300), 'toBlock': hex(block + 5), 'topics': [TOPIC_MIGRATED]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(amount, gross, cap, max_fee, tip, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(amount, cap), 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
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
    common = dict(hash=tx_hash, amount_wei=amount, expected_gross_wei=gross, cap_wei=cap, gas_limit=gas_limit,
                  max_fee_wei=max_fee, tip_wei=tip)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee', '0x0'), 16)
    try:
        winner = block if status else last_migration_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        net_wei=(gross - cost) if status else -cost, send_block=block, winner_block=winner,
        tx_index=int(receipt['transactionIndex'], 16), **common)


def check():
    """One look: 1 eth_call when nothing is open. Returns True when a gain above MIN_INTEREST was seen."""
    gains = probe(SIZES)
    gross = max(gains)
    if gross < MIN_INTEREST_WEI:
        return False
    amount = SIZES[gains.index(gross)]
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(take_calldata(amount, 1))), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', amount_wei=amount, gross_wei=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 12 // 10
    tip = max(TIP_MIN_WEI, min(TIP_MAX_WEI, gross // TIP_SHARE_DEN // gas_limit))
    max_fee = base_fee + base_fee // 4 + tip
    cap = gas_limit * max_fee + L1_FEE_ALLOW_WEI      # the most this send is expected to cost (L2 bound + L1 allowance)
    cap_usd = cap / 1e18 * ETH_REF_USD
    log('opportunity', amount_wei=amount, gross_wei=gross, gains_wei=gains, cap_wei=cap, base_fee=base_fee, tip_wei=tip,
        max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit, cap_usd=round(cap_usd, 4))
    if max_fee > MAX_FEE_CAP_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', max_fee_wei=max_fee, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross * SEND_MULT_DEN <= cap * SEND_MULT_NUM:   # send only when expected gross > 1.3 x this send's cost cap
        log('opportunity_skip', reason='gross_below_send_line', gross_wei=gross, cap_wei=cap)
        return True
    checked, err = gain_of(amount, cap, gas_limit)     # the exact call that would be signed (minProfit = cost cap)
    if checked <= cap:
        log('simulate_revert', step='guard', amount_wei=amount, gross_wei=gross, cap_wei=cap, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', amount_wei=amount, gross_wei=checked, cap_wei=cap, gas_estimate=estimate,
            gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    else:
        # Base: the L1 data fee is not bounded by the signed tx, so the worst case of a send is the wallet balance.
        usd = wallet_usd()
        if usd >= WALLET_MAX_USD:
            log('opportunity_skip', reason='wallet_at_or_above_usd_bound', wallet_usd=round(usd, 4))
            return True
        send_live(amount, checked, cap, max_fee, tip, gas_limit)
    return True


def feed_wait(cursor, timeout):
    """Long-poll the farm feed for Transfer of the two TEL tokens (one filter). Returns the feed's JSON ({'cursor', 'logs'}
    plus 'timeout' or 'gap'). HTTP 429 / 503 and connection errors raise (the caller re-reads state)."""
    q = {'address': ','.join(FEED_ADDRESSES), 'topic0': TOPIC_TRANSFER, 'timeout': str(int(timeout))}
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
    log('start', mode=MODE, executor=executor(), migrator=MIGRATOR, sizes=len(SIZES), trigger='feed Transfer',
        feed_address=FEED_ADDRESSES, feed_topic0=TOPIC_TRANSFER, safety_poll_seconds=SAFETY_POLL, follow_ups=list(FOLLOW_UPS))
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
                    wait = MIN_LOOK_GAP - (time.time() - s['last_check'])
                    if wait > 0:
                        time.sleep(wait)       # a burst of transfers is one look, on the state after it
                    log('feed', events=len(logs), blocks=sorted({int(x['blockNumber'], 16) for x in logs})[-4:],
                        txs=sorted({x['transactionHash'] for x in logs})[:2])
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
