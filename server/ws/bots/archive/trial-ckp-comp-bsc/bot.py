#!/usr/bin/env python3
"""trial: Cakepie CKP compensation on BSC. The Cakepie compensation contract (0x7ae3f267..., proxy, opened about
2026-11-20) pays a fixed 0.5199 USDT for every CKP burnt through it, to anyone: compensate(amount) pulls and burns
the caller's CKP, claim() pays the USDT. When a holder sells CKP into the PancakeSwap V3 WBNB / CKP pool
(0x8b626acf...) the pool price falls below that rate and one transaction closes the gap through the CompensationArb
executor: flash swap on the PancakeSwap V3 USDT / WBNB pool (sell USDT, receive WBNB first) -> WBNB to CKP on the CKP
pool -> compensate + claim -> repay the USDT pool from the claim -> sell the USDT left for WBNB -> unwrap -> pay the
bot wallet in BNB. The executor reverts unless the wallet is paid at least minProfit.
Feed bot: it waits on the farm feed for Swap on the CKP pool (a CKP seller opens the gap), re-reads on a gap /
429 / 503 / connection error and on a 120 s safety poll (a BNB price move opens it too). Each look is ONE eth_call of
the executor's probe() over a grid of sizes. It sends when the best size pays more than 1.3 x the send's cost cap."""
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

# Addresses: the receipt and call trace of incumbent take 0xacb524e56f3eb18441163786e11f9363a9685131d365d06b469a53ed37101f10
# (block 134,815,627), the compensation contract's own getters CKP() / USDT() and token0() / token1() of both pools,
# read on 2026-11-22 (scratch/trial-ckp-comp-bsc/proof.py asserts them again on the fork).
COMP = '0x7ae3f2672486ada489e41e8a23bba414ee7db4c7'         # Cakepie compensation proxy: compensate(uint256), claim()
CKP = '0x2b5d9adea07b590b638ffc165792b2c610eda649'          # Cakepie token, burnt by compensate
USDT = '0x55d398326f99059ff775485246999027b3197955'         # BSC-USD, 18 decimals, paid by claim
WBNB = '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'
POOL_USDT_WBNB = '0x172fcd41e0913e95784454622d1c3724f546f849'   # PancakeSwap V3 USDT (token0) / WBNB (token1): flash swap and exit
POOL_WBNB_CKP = '0x8b626acfb32cdad0d2f3b493eb9928bba1bbbcca'    # PancakeSwap V3 CKP (token0) / WBNB (token1), fee 2500
# USDT sold into the flash pool each look: 5 x 1.6^k, k = 0..12 (5 .. 1,407 USDT; incumbent takes were 10-742 USDT)
SIZES = [int(5 * 10**18 * 1.6**k) for k in range(13)]

# Selectors and topics from `cast sig` / `cast keccak` (checked again by scratch/trial-ckp-comp-bsc/proof.py).
ARB_TYPES = '(address,address,address,address,address,address,address,address,uint256,uint256)'
SEL_RUN = '0xcbab0948'      # run(ARB_TYPES)
SEL_PROBE = '0x397bc4c1'    # probe(ARB_TYPES[])
TOPIC_SWAP = '0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83'   # PancakeV3 Swap(address,address,int256,int256,uint160,uint128,int24,uint128,uint128)
TOPIC_COMPENSATED = '0x3fc2682c72ca4b385712df78cbb3df71f24e438d7bec95d338a1ddf28b410f54'   # Compensated(address,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000f11ac'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_BSC') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BSC or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546').rstrip('/')   # farm-feed (wiki infra/feed.md)
FEED_ADDRESSES = [POOL_WBNB_CKP]   # ONE filter: Swap on the CKP pool
FEED_TOPICS = [TOPIC_SWAP]
FEED_TIMEOUT = 55                  # long-poll seconds
FEED_DOWN_POLL = 60                # while the feed answers 429 / 503 / errors: one state re-read at most this often
SAFETY_POLL = 120                  # seconds: a look even when the feed is silent (720 a day x 26 CU = 18,720 CU);
#                                    CKP is priced in WBNB, so a BNB price move opens the gap with no swap on the CKP pool
FOLLOW_UPS = (3, 10, 30)           # extra looks after a look that saw a gain (a send that lost, a second seller)

MIN_INTEREST_WEI = 2 * 10**13      # 0.00002 BNB (about 0.01 USD): below this nothing is logged
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send only when gross > 1.3 x the send's cost cap
TIP_SHARE_DEN = 3                  # gas price bid: at most 1/3 of gross spread over the gas limit ...
GAS_PRICE_MAX_WEI = 6 * 10**8      # ... and never above 0.6 gwei (the BSC floor is 0.05 gwei)
GAS_LIMIT_MAX = 1_500_000          # a take uses about 0.45-0.6M gas; eth_estimateGas x 1.25 on top
BNB_REF_USD = 1500.0               # deliberately high BNB price for the USD cap (BNB was about 545 USD on 2026-11-22)
MAX_TX_USD = 0.95
CU_CAP = 95_000
CU_COST = {'eth_call': 26, 'eth_gasPrice': 10, 'eth_estimateGas': 20, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_getLogs': 75}

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
    return (a(COMP) + a(CKP) + a(USDT) + a(POOL_USDT_WBNB) + a(WBNB) + a(POOL_WBNB_CKP) + a(POOL_USDT_WBNB) + a(WBNB)
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
    """Block of the newest Compensated log near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': COMP, 'fromBlock': hex(block - 200), 'toBlock': hex(block + 5),
                                'topics': [TOPIC_COMPENSATED]}])
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
    common = dict(hash=tx_hash, amount_usdt_wei=amount, expected_gross_wei=gross, cap_wei=cap,
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
        log('simulate_revert', step='estimate', amount_usdt_wei=amount, gross_wei=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 5 // 4
    gas_price = max(floor_price, min(GAS_PRICE_MAX_WEI, gross // TIP_SHARE_DEN // gas_limit))
    cap = gas_limit * gas_price                        # the most this send can cost (maxFeePerGas x gasLimit)
    cap_usd = cap / 1e18 * BNB_REF_USD
    log('opportunity', amount_usdt_wei=amount, gross_wei=gross, gains_wei=gains, cap_wei=cap, floor_price_wei=floor_price,
        gas_price_wei=gas_price, gas_estimate=estimate, gas_limit=gas_limit, cap_usd=round(cap_usd, 4))
    if gas_price > GAS_PRICE_MAX_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', gas_price_wei=gas_price, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross * SEND_MULT_DEN <= cap * SEND_MULT_NUM:   # send only when expected gross > 1.3 x this send's cost cap
        log('opportunity_skip', reason='gross_below_send_line', gross_wei=gross, cap_wei=cap)
        return True
    checked, err = gain_of(amount, cap, gas_limit)     # the exact call that would be signed (minProfit = cap)
    if checked <= cap:
        log('simulate_revert', step='guard', amount_usdt_wei=amount, gross_wei=gross, cap_wei=cap, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', amount_usdt_wei=amount, gross_wei=checked, cap_wei=cap,
            gas_estimate=estimate, gas_limit=gas_limit, gas_price_wei=gas_price)
    else:
        send_live(amount, checked, cap, gas_price, gas_limit)
    return True


def feed_wait(cursor, timeout):
    """Long-poll the farm feed for Swap on the CKP pool (one filter). Returns the feed's JSON ({'cursor', 'logs'} plus
    'timeout' or 'gap'). HTTP 429 / 503 and connection errors raise (the caller re-reads)."""
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
    log('start', mode=MODE, executor=executor(), comp=COMP, ckp_pool=POOL_WBNB_CKP, flash_pool=POOL_USDT_WBNB,
        sizes=len(SIZES), trigger='feed Swap on the CKP pool', feed_address=FEED_ADDRESSES, feed_topic0=FEED_TOPICS,
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
