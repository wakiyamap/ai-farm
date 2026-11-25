#!/usr/bin/env python3
"""trial: old ARC (0x5a4342f4...) against new ARC (0x431151f2...) on Base. The migrator 0xa1bc813c... has a public
migrate(uint256): it burns old ARC and pays new ARC at 40 old : 1 new (at most 100,000 old per call, whole new tokens
only). Old ARC still trades in a Uniswap V2 pair against VIRTUAL, new ARC in a V2 pair against WETH. When old ARC is
cheap, one transaction through the TokenMigrateArb executor does: Morpho flash loan of WETH -> VIRTUAL -> old ARC ->
migrate -> new ARC -> WETH -> repay -> unwrap the rest to the bot wallet. The executor reverts unless the wallet is paid
at least minProfit. Feed bot: it waits on the farm feed for a Sync on the old-ARC pair or the new-ARC pair (24 logs a
day together), then does ONE eth_call of the executor's probe() (a grid of loan sizes); it looks again on a gap / 429 /
503 / connection error, on a 300 s safety poll and on a few follow-ups while a gain stands."""
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

# Addresses: all from the receipt of incumbent take 0x8e5762f2f1293648084a55d7e2c2bc1f01f6a49ec06142a10c69c29920119450
# (block 60,393,655); token0()/token1()/factory() of each pair read on chain (scratch/r0891/facts.py).
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'      # Morpho Blue: flashLoan, no fee
WETH = '0x4200000000000000000000000000000000000006'
OLD = '0x5a4342f4268a731f4459cd0be22d4744a86d635d'         # old ARC (1 pct transfer tax out of its pair)
NEW = '0x431151f26c48b4d4befc34048a0966bf960a0c50'         # new ARC
MIGRATOR = '0xa1bc813c3323335407ee2c2330f6a0f3b7437cdb'    # migrate(uint256) 0x454b0608, public
BUY_PAIRS = ['0xe31c372a7af875b3b5e0f3713b17ef51556da667',  # Uniswap V2 VIRTUAL / WETH
             '0xb68f6d542bee0e2a3a0df0de4a2d7d76ffff924a']  # Uniswap V2 VIRTUAL / old ARC
SELL_PAIRS = ['0x2814a97ec973e523e8207e48227bcdc07ca10027']  # Uniswap V2 WETH / new ARC
UNIT = 40 * 10**18                 # 40 old = 1 new; the incumbents migrate whole new tokens only
CHUNK = 100_000 * 10**18           # most old ARC per migrate() call (every Migrated log of 7 days: <= 100,000)
FEE1000 = 997
# loan sizes probed each look (wei of WETH): 0.0004 x 1.6^k, k = 0..12 (0.0004 .. 0.113; incumbents: 0.0018 typical)
SIZES = [int(4 * 10**14 * 1.6**k) for k in range(13)]

# Selectors, all from `cast sig` (checked again by scratch/trial-arc-migrate-base/proof.py).
SEL_TAKE = '0xd9d6260f'    # take((address,address,address[],address[],address,address,address,uint256,uint256,uint256,uint256,uint256))
SEL_PROBE = '0xeacb2e9f'   # probe((...)[])
TOPIC_MIGRATED = '0xb448784ad03c657e3d056f1060b743044d5117af071328a69576d187b180bb31'   # migrator event, from that receipt

PAPER_EXEC = '0x00000000000000000000000000000000000f11a9'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546').rstrip('/')   # farm-feed (wiki infra/feed.md)
# Trigger: ONE feed /logs filter = the old-ARC pair and the new-ARC pair, topic0 = V2 Sync (cast keccak
# "Sync(uint112,uint112)"; 10 + 14 logs in 24 h, scratch/trial-arc-migrate-base/feedcheck.py). The busy VIRTUAL / WETH
# pair is NOT subscribed; its drift is seen by the safety poll.
FEED_ADDRESSES = [BUY_PAIRS[1], SELL_PAIRS[0]]
TOPIC_SYNC = '0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'
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
ETH_REF_USD = 4000.0               # deliberately high ETH price for the USD cap (ETH was about 1,820 USD on 2026-11-22)
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


def take_tuple(borrow, min_profit):
    """ABI encoding of one Take struct (dynamic: two address arrays)."""
    head_words = 12
    off_buy = head_words * 32
    off_sell = off_buy + 32 * (1 + len(BUY_PAIRS))
    return (a(MORPHO) + a(WETH) + w(off_buy) + w(off_sell) + a(OLD) + a(NEW) + a(MIGRATOR) + w(UNIT) + w(CHUNK)
            + w(FEE1000) + w(borrow) + w(min_profit)
            + w(len(BUY_PAIRS)) + ''.join(a(p) for p in BUY_PAIRS)
            + w(len(SELL_PAIRS)) + ''.join(a(p) for p in SELL_PAIRS))


def take_calldata(borrow, min_profit):
    return SEL_TAKE + w(32) + take_tuple(borrow, min_profit)


def probe_calldata(sizes):
    items = [take_tuple(s, 1) for s in sizes]
    offs, pos = [], 32 * len(items)
    for it in items:
        offs.append(pos)
        pos += len(it) // 2
    return SEL_PROBE + w(32) + w(len(items)) + ''.join(w(o) for o in offs) + ''.join(items)


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


def probe(sizes, block='latest'):
    """Gains (wei of WETH) of each loan size on chain in ONE eth_call; 0 = that take would revert."""
    res = rpc('eth_call', call_params(probe_calldata(sizes), None, block)).removeprefix('0x')
    words = [int(res[i:i + 64], 16) for i in range(0, len(res), 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(sizes):
        raise RuntimeError('probe: unexpected return length')
    return gains


def gain_of(borrow, min_profit, gas_limit=None):
    """Return value of the exact take() as an eth_call; 0 when it reverts."""
    ans = rpc('eth_call', call_params(take_calldata(borrow, min_profit), gas_limit), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def last_migration_block(block):
    """Block of the newest migration near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': MIGRATOR, 'fromBlock': hex(block - 300), 'toBlock': hex(block + 5), 'topics': [TOPIC_MIGRATED]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(borrow, gross, cap, max_fee, tip, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(borrow, cap), 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
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
    common = dict(hash=tx_hash, borrow_wei=borrow, expected_gross_wei=gross, cap_wei=cap, gas_limit=gas_limit,
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
    borrow = SIZES[gains.index(gross)]
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(take_calldata(borrow, 1))), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', borrow_wei=borrow, gross_wei=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 12 // 10
    tip = max(TIP_MIN_WEI, min(TIP_MAX_WEI, gross // TIP_SHARE_DEN // gas_limit))
    max_fee = base_fee + base_fee // 4 + tip
    cap = gas_limit * max_fee + L1_FEE_ALLOW_WEI      # the most this send is expected to cost (L2 bound + L1 allowance)
    cap_usd = cap / 1e18 * ETH_REF_USD
    log('opportunity', borrow_wei=borrow, gross_wei=gross, gains_wei=gains, cap_wei=cap, base_fee=base_fee, tip_wei=tip,
        max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit, cap_usd=round(cap_usd, 4))
    if max_fee > MAX_FEE_CAP_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', max_fee_wei=max_fee, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross * SEND_MULT_DEN <= cap * SEND_MULT_NUM:   # send only when expected gross > 1.3 x this send's cost cap
        log('opportunity_skip', reason='gross_below_send_line', gross_wei=gross, cap_wei=cap)
        return True
    checked, err = gain_of(borrow, cap, gas_limit)     # the exact call that would be signed (minProfit = cost cap)
    if checked <= cap:
        log('simulate_revert', step='guard', borrow_wei=borrow, gross_wei=gross, cap_wei=cap, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', borrow_wei=borrow, gross_wei=checked, cap_wei=cap, gas_estimate=estimate,
            gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    else:
        send_live(borrow, checked, cap, max_fee, tip, gas_limit)
    return True


def feed_wait(cursor, timeout):
    """Long-poll the farm feed for Sync on the two ARC pairs (one filter). Returns the feed's JSON ({'cursor', 'logs'}
    plus 'timeout' or 'gap'). HTTP 429 / 503 and connection errors raise (the caller re-reads state)."""
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
    log('start', mode=MODE, executor=executor(), migrator=MIGRATOR, sizes=len(SIZES), trigger='feed Sync',
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
