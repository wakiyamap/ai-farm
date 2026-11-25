#!/usr/bin/env python3
"""trial: Solv xSolvBTC instant withdraw on BSC. Solv's XSolvBTCPool (0xf5086053..., proxy) lets anyone burn xSolvBTC
and be paid SolvBTC at the share value (getValueByShares) minus a 0.05 % fee in the same call: withdraw(uint256), no
allowlist (deposit is allowlisted, so the class only runs one way). When a holder sells xSolvBTC into the PancakeSwap
V3 xSolvBTC / SolvBTC pool (0x5a5ca751...) instead of withdrawing, the pool price falls below that value and one
transaction closes the gap through the ShareRedeemArb executor: flash swap on that pool (sell SolvBTC, receive
xSolvBTC first) -> withdraw the xSolvBTC -> repay the pool in SolvBTC from the redemption -> sell the SolvBTC left
for BTCB -> BTCB for WBNB -> unwrap -> pay the bot wallet in BNB. The executor reverts unless the wallet is paid at
least minProfit.
Feed bot: it waits on the farm feed for Swap on the xSolvBTC pool (a seller opens the gap), re-reads on a gap /
429 / 503 / connection error and on a 120 s safety poll. Each look is ONE eth_call of the executor's probe() over a
grid of sizes. It sends when the best size pays more than 1.3 x the send's cost cap."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545').rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'bsc'

# Addresses: the receipt and call trace of incumbent take 0x2cd7b02da34caa2bec20698189d2aa59f32d2eafeb6c6e444d98d144c5932c51
# (block 135,137,431) and token0() / token1() of the pools, read on 2026-11-22
# (scratch/trial-xsolvbtc-redeem-bsc/proof.py asserts them again on the fork).
REDEEMER = '0xf50860533d209e44dbe02f58b77ea85a8bfc28a3'     # Solv XSolvBTCPool proxy: withdraw(uint256)
XSOLV = '0x1346b618dc92810ec74163e4c27004c921d446a5'        # xSolvBTC, burnt by withdraw
SOLV = '0x4aae823a6a0b376de6a78e74ecc5b079d38cbcf7'         # SolvBTC, 18 decimals, minted by withdraw
BTCB = '0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c'
WBNB = '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'
POOL_X = '0x5a5ca75147550079411f6f543b729a4beab4dfeb'       # PancakeSwap V3 xSolvBTC / SolvBTC: the flash swap
POOL_SOLV_BTCB = '0x12197d7a4fe2d67f9f97ae64d82a44c24b7ad407'   # PancakeSwap V3 SolvBTC / BTCB: first exit hop
POOL_BTCB_WBNB = '0x62edaf2a56c9fb55be5f9b1399ac067f6a37013b'   # PancakeSwap V3 BTCB / WBNB: second exit hop
# SolvBTC sold into the flash pool each look: 0.0002 x 1.8^k BTC, k = 0..12 (0.0002 .. 0.23 BTC; the incumbent
# takes 0.0016 BTC lots)
SIZES = [int(2 * 10**14 * 1.8**k) for k in range(13)]

# Selectors and topics from `cast sig` / `cast keccak` (checked again by scratch/trial-xsolvbtc-redeem-bsc/proof.py).
ARB_TYPES = '(address,address,address,address,address,address,address,address,uint256,uint256)'
SEL_RUN = '0xcbab0948'      # run(ARB_TYPES)
SEL_PROBE = '0x397bc4c1'    # probe(ARB_TYPES[])
TOPIC_SWAP = '0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83'   # PancakeV3 Swap(address,address,int256,int256,uint160,uint128,int24,uint128,uint128)
TOPIC_WITHDRAW = '0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'   # Withdraw(address,address,address,uint256,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000f11ad'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_BSC') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BSC or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546').rstrip('/')   # farm-feed (wiki infra/feed.md)
FEED_ADDRESSES = [POOL_X]          # ONE filter: Swap on the xSolvBTC / SolvBTC pool
FEED_TOPICS = [TOPIC_SWAP]
FEED_TIMEOUT = 55                  # long-poll seconds
FEED_DOWN_POLL = 60                # while the feed answers 429 / 503 / errors: one state re-read at most this often
SAFETY_POLL = 120                  # seconds: a look even when the feed is silent (720 a day x 26 CU = 18,720 CU);
#                                    the share value rises with yield, which opens the gap with no swap on the pool
FOLLOW_UPS = (3, 10, 30) if MODE == 'live' else ()   # extra looks after a look that saw a gain (a send that lost, a
#                                    second seller). None in paper: a standing gain is never taken there, and
#                                    follow-ups on every look would spend the CU cap (720 looks x 82 CU = 59,000 a day)

MIN_INTEREST_WEI = 6 * 10**13      # 0.00006 BNB (about 0.03 USD, just above 1.3 x a floor-price gas cap of about
#                                    0.000043 BNB): below this nothing is logged or estimated. After a take about
#                                    0.00002 BNB is left in the pool (fork: probe_after), which must not cost reads
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send only when gross > 1.3 x the send's cost cap
TIP_SHARE_DEN = 3                  # gas price bid: at most 1/3 of gross spread over the gas limit ...
GAS_PRICE_MAX_WEI = 6 * 10**8      # ... and never above 0.6 gwei (the BSC floor is 0.05 gwei)
GAS_LIMIT_MAX = 1_500_000          # a take uses about 0.6M gas; eth_estimateGas x 1.25 on top
BNB_REF_USD = 1500.0               # deliberately high BNB price for the USD cap (BNB was about 600 USD on 2026-11-22)
MAX_TX_USD = 0.95
CU_CAP = 95_000
CU_COST = {'eth_call': 26, 'eth_gasPrice': 10, 'eth_estimateGas': 20, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_getLogs': 75}

BACKOFF = {'losses': 0, 'until': 0}   # live only: pause between sends after a lost one (see send_live)
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


def arb_tuple(amount, min_profit):
    """ABI encoding of one Arb struct (static: 10 words)."""
    return (a(REDEEMER) + a(XSOLV) + a(SOLV) + a(POOL_X) + a(POOL_SOLV_BTCB) + a(BTCB) + a(POOL_BTCB_WBNB) + a(WBNB)
            + w(amount) + w(min_profit))


def run_calldata(amount, min_profit):
    return SEL_RUN + arb_tuple(amount, min_profit)


def probe_calldata(sizes):
    return SEL_PROBE + w(32) + w(len(sizes)) + ''.join(arb_tuple(s, 1) for s in sizes)


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
    """What each size would pay (wei of BNB) in ONE eth_call; 0 = that run would revert."""
    res = rpc('eth_call', call_params(probe_calldata(sizes), None, block)).removeprefix('0x')
    words = [int(res[i:i + 64], 16) for i in range(0, len(res), 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(sizes):
        raise RuntimeError('probe: unexpected return length')
    return gains


def gain_of(amount, min_profit, gas_limit=None):
    """Return value of the exact run() as an eth_call; 0 when it reverts."""
    ans = rpc('eth_call', call_params(run_calldata(amount, min_profit), gas_limit), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def last_take_block(block):
    """Block of the newest Withdraw log of the redeemer near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': REDEEMER, 'fromBlock': hex(block - 200), 'toBlock': hex(block + 5),
                                'topics': [TOPIC_WITHDRAW]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(amount, gross, cap, gas_price, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, run_calldata(amount, cap), 0, gas_limit, gas_price,
                                max_priority_fee_per_gas=gas_price)
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
    common = dict(hash=tx_hash, amount_solvbtc_wei=amount, expected_gross_wei=gross, cap_wei=cap,
                  gas_limit=gas_limit, gas_price_wei=gas_price)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        winner = block if status else last_take_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        net_wei=(gross - cost) if status else -cost, send_block=block, winner_block=winner,
        tx_index=int(receipt['transactionIndex'], 16), **common)
    # back-off after a lost send: 60 s, 120 s, ... up to 1 h, reset by a win (a standing gain that the chain does not
    # pay must not be re-sent at every look)
    if status:
        BACKOFF['losses'] = 0
        BACKOFF['until'] = 0
    else:
        BACKOFF['losses'] += 1
        BACKOFF['until'] = time.time() + min(3600, 60 * 2 ** (BACKOFF['losses'] - 1))


def check():
    """One look: 1 eth_call when nothing is open. Returns True when a gain worth logging was seen."""
    gains = probe(SIZES)
    gross = max(gains)
    if gross < MIN_INTEREST_WEI:
        return False
    amount = SIZES[gains.index(gross)]
    floor_price = int(rpc('eth_gasPrice', []), 16)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(run_calldata(amount, 1))), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', amount_solvbtc_wei=amount, gross_wei=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 5 // 4
    gas_price = max(floor_price, min(GAS_PRICE_MAX_WEI, gross // TIP_SHARE_DEN // gas_limit))
    cap = gas_limit * gas_price                        # the most this send can cost (maxFeePerGas x gasLimit)
    cap_usd = cap / 1e18 * BNB_REF_USD
    log('opportunity', amount_solvbtc_wei=amount, gross_wei=gross, gains_wei=gains, cap_wei=cap, floor_price_wei=floor_price,
        gas_price_wei=gas_price, gas_estimate=estimate, gas_limit=gas_limit, cap_usd=round(cap_usd, 4))
    if gas_price > GAS_PRICE_MAX_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', gas_price_wei=gas_price, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross * SEND_MULT_DEN <= cap * SEND_MULT_NUM:   # send only when expected gross > 1.3 x this send's cost cap
        log('opportunity_skip', reason='gross_below_send_line', gross_wei=gross, cap_wei=cap)
        return False                                   # nothing to follow up: no extra looks for a gain it will not send for
    checked, err = gain_of(amount, cap, gas_limit)     # the exact call that would be signed (minProfit = cap)
    if checked <= cap:
        log('simulate_revert', step='guard', amount_solvbtc_wei=amount, gross_wei=gross, cap_wei=cap, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', amount_solvbtc_wei=amount, gross_wei=checked, cap_wei=cap,
            gas_estimate=estimate, gas_limit=gas_limit, gas_price_wei=gas_price)
    elif time.time() < BACKOFF['until']:
        log('opportunity_skip', reason='backoff_after_lost_send', losses=BACKOFF['losses'],
            seconds_left=int(BACKOFF['until'] - time.time()))
    else:
        send_live(amount, checked, cap, gas_price, gas_limit)
    return True


def feed_wait(cursor, timeout):
    """Long-poll the farm feed for Swap on the xSolvBTC pool (one filter). Returns the feed's JSON ({'cursor', 'logs'}
    plus 'timeout' or 'gap'). HTTP 429 / 503 and connection errors raise (the caller re-reads)."""
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
    log('start', mode=MODE, executor=executor(), redeemer=REDEEMER, flash_pool=POOL_X, exit_pools=[POOL_SOLV_BTCB, POOL_BTCB_WBNB],
        sizes=len(SIZES), trigger='feed Swap on the xSolvBTC / SolvBTC pool', feed_address=FEED_ADDRESSES, feed_topic0=FEED_TOPICS,
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
