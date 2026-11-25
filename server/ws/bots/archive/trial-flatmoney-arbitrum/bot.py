#!/usr/bin/env python3
"""Trial: Flat Money (Arbitrum) delayed-order keeper through the FlatOrderKeeper executor.

Waits on the farm feed for OrderAnnounced. An announced order becomes executable 5 s after its
announce block and pays its keeperFee (about 200-260 sat WBTC) to whoever calls executeOrder with a
Pyth WBTC/USD update published at or after that time. The bot sleeps until then, fetches the
update from the local Hermes proxy, simulates the executor call (executeOrder + sell the fee to
WETH + unwrap, reverts unless native grows) and, live, sends it. A lost attempt costs gas only.
"""
import concurrent.futures
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546')
HERMES = os.environ.get('HERMES_URL', 'http://127.0.0.1:29486')   # local keyless proxy
CHAIN = 'arbitrum'
ANN = '0x2326bb21b769d81e134c9b305ca156f989249fe7'       # OrderAnnouncementModule proxy
MODULE = '0x7e50ad6e467d9fafc3b4bfd003247ceaa2f17e5b'    # OrderExecutionModule proxy
WBTC = '0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f'      # vault collateral = keeper fee token
WETH = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'
POOL = '0x2f5e87c9312fa29aed5c179e456625d79015299c'      # UniV3 WBTC/WETH 0.05%
T_ANNOUNCED = '0x0aaed4f1864bd4663319a4a0ceb0b5f0766e7e58ee27cf50c48232258d5f582c'  # OrderAnnounced
T_EXECUTED = '0x0033bce9199bd52d311031877abb23eb96f48c0233bcff63a4e4acb31896ce37'   # OrderExecuted
FEED_WBTC = 'c9d8b075a5c69303365ae23633d4e085199bf5c520a3b90fed1322a0342ffc33'      # Pyth WBTC/USD
FEED_ETH = 'ff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace'       # Pyth ETH/USD
SEL_RUN = '0x66080ff4'   # run(address,address,bytes[],address,address,address,uint256)
PAPER_EXEC = '0xfe00ddfee1423e3dba3e07a1b0f78b0ac1df8e9a'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000002'
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

MIN_AGE = 5                    # minExecutabilityAge (s): executable at announce block time + 5
MAX_AGE = 60                   # maxExecutabilityAge (s): the order expires after that
TRY_FOR = 20.0                 # stop trying this long after executableAt (incumbent lands at +2..6 s)
TRY_GAP = 0.35                 # pause between tries
MAX_TRIES = 12                 # relay reads per order are bounded: 12 x (eth_call + estimateGas)
# ---- loss guard (trial rule: every send's gas cap < 1 USD) ----
GAS_HARD_MAX = 3_000_000       # an estimate above this is not sent
GAS_MARGIN = 1.30              # gas limit = eth_estimateGas x 1.30 (Arbitrum: never a constant)
PAPER_GAS = 1_300_000          # paper only, when the node cannot estimate with a code override
SEND_CAP_USD = 0.95            # gasLimit x maxFeePerGas of one send must stay under this (< 1 USD)
ETH_MARGIN = 1.15              # ETH valued 15% above the Hermes ETH/USD read when sizing the cap
ETH_FALLBACK_USD = 4000.0      # used when Hermes ETH/USD is unreadable
ETH_MIN_USD = 1000.0           # an implausibly low read falls back to the high value
GROSS_SHARE = 0.90             # gasLimit x maxFeePerGas <= 90% of simulated gross
BID_SHARE = 0.20               # priority fee bid is at most 20% of simulated gross
SAFETY_POLL = 600
LOOKBACK_BLOCKS = 280          # about 70 s of Arbitrum blocks: every order that can still be live
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10,
           'eth_gasPrice': 10, 'eth_estimateGas': 20, 'eth_getBlockByNumber': 20,
           'eth_getTransactionByHash': 20}
CU_CAP = 60_000                # relay reads/day; the feed filter (about 6k CU/day) is on top
_id = 0
_eth = {'usd': None, 'at': 0}
_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': time.time(), 'ev': ev, **kw}
    with LOG.open('a') as f:
        f.write(json.dumps(row, separators=(',', ':'), default=str) + '\n')


def spend(method):
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(CU_FILE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    cost = CU_COST.get(method, 26)
    if budget['cu'] + cost > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} relay CU/day bot cap reached')
    budget['cu'] += cost
    CU_FILE.write_text(json.dumps(budget))


def rpc_raw(method, params, rid):
    body = json.dumps({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {json.dumps(ans["error"])[:300]}')
    return ans['result']


def rpc(method, params):
    global _id
    spend(method)          # budget is counted on the main thread only
    _id += 1
    return rpc_raw(method, params, _id)


def word(n):
    return format(n, '064x')


def aw(a):
    return a.lower().removeprefix('0x').zfill(64)


def hermes(feed_id, binary):
    """Latest Pyth update for one feed: (publish_time, price float, update bytes or None)."""
    q = urllib.parse.urlencode({'ids[]': feed_id, 'parsed': 'true', 'encoding': 'hex'})
    with urllib.request.urlopen(f'{HERMES}/v2/updates/price/latest?{q}', timeout=5) as r:
        d = json.load(r)
    p = d['parsed'][0]['price']
    blob = bytes.fromhex(d['binary']['data'][0]) if binary else None
    return int(p['publish_time']), int(p['price']) * 10 ** int(p['expo']), blob


def eth_ref_usd():
    """ETH price used to turn the fee cap into USD: Hermes read plus a margin, never a low guess."""
    now = time.time()
    if now - _eth['at'] > 900:
        _eth['at'] = now
        try:
            _, px, _ = hermes(FEED_ETH, False)
            _eth['usd'] = px
        except Exception as e:
            _eth['usd'] = None
            log('eth_price_error', error=str(e)[:160])
    if _eth['usd'] is None or _eth['usd'] < ETH_MIN_USD:
        return ETH_FALLBACK_USD
    return _eth['usd'] * ETH_MARGIN


def calldata(account, blob, min_profit):
    """run(module, account, bytes[] update, feeToken, pool, weth, minProfit); one update blob.
    Head = 7 words, array offset 0xe0; checked against `cast calldata` in the fork proof."""
    enc = word(len(blob)) + blob.hex().ljust(((len(blob) + 31) // 32) * 64, '0')
    arr = word(1) + word(32) + enc
    return (SEL_RUN + aw(MODULE) + aw(account) + word(7 * 32) + aw(WBTC) + aw(POOL) + aw(WETH)
            + word(min_profit) + arr)


def owner():
    sys.path.append('/opt/farm/lib')   # the live service does not put it on the path
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a['address'] if isinstance(a, dict) else a
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def sim_and_estimate(data, from_addr, exec_addr, code):
    """eth_call (native gain in wei) and eth_estimateGas of the same bytes, side by side.
    Returns (gain, gas_limit, estimated). Raises when the call reverts."""
    tx = {'from': from_addr, 'to': exec_addr, 'data': data}
    over = [{exec_addr: {'code': code}}] if code else []
    spend('eth_call')
    spend('eth_estimateGas')
    f_call = _pool.submit(rpc_raw, 'eth_call', [tx, 'latest'] + over, 1)
    f_est = _pool.submit(rpc_raw, 'eth_estimateGas', [tx] + (['latest'] + over if over else []), 2)
    gain = int(f_call.result(), 16)          # raises on revert
    try:
        est = int(f_est.result(), 16)
    except Exception:
        if code is None:
            raise                            # live: no estimate = no send
        return gain, PAPER_GAS, False        # paper: the node may refuse a code override
    return gain, int(est * GAS_MARGIN), True


def taker(account, from_block):
    """Who executed this account's order: (block, tx hash, tx sender) or None."""
    logs = rpc('eth_getLogs', [{'address': MODULE, 'fromBlock': hex(from_block), 'toBlock': 'latest',
                               'topics': [T_EXECUTED]}])
    for x in logs:
        if x['data'][2:66][-40:] == account[2:].lower():
            h = x['transactionHash']
            try:
                frm = rpc('eth_getTransactionByHash', [h])['from']
            except ReadBudgetExceeded:
                raise
            except Exception:
                frm = None
            try:
                ts = block_ts(x)
            except ReadBudgetExceeded:
                raise
            except Exception:
                ts = None
            return {'block': int(x['blockNumber'], 16), 'hash': h, 'from': frm, 'block_ts': ts,
                    'tx_index': int(x['transactionIndex'], 16)}
    return None


def send_live(account, data, gas_limit, max_fee, priority, gain, ann_block, exec_at):
    sys.path.append('/opt/farm/lib')
    import farmbot_signer
    t_send = time.time()
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', account=account, reply=reply)  # final: no retry
        return
    receipt = None
    for _ in range(30):  # arbitrum blocks are ~0.25 s; give up after 15 s
        time.sleep(0.5)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt:
            break
    try:
        win = taker(account, ann_block)
    except Exception:
        win = None
    if not receipt:
        log('send_result', hash=h, account=account, result='unknown', gas_used=None,
            winner_block=win and win['block'], winner=win)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    price = int(receipt['effectiveGasPrice'], 16)
    log('send_result', hash=h, account=account, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * price, send_block=b, winner_block=win and win['block'], winner=win,
        blocks_after_winner=(b - win['block'] if win else None), gain_wei=gain,
        sent_s_after_executable=round(t_send - exec_at, 2))


def handle(s, account, order_type, keeper_fee, ann_block, ann_ts):
    """One announced order: wait until it is executable, then try until taken or TRY_FOR passes."""
    exec_at = ann_ts + MIN_AGE
    key = f'{account}:{ann_block}'
    if key in s['done']:
        return
    s['done'][key] = time.time()
    now = time.time()
    if now > exec_at + TRY_FOR:
        log('order_skip', account=account, ann_block=ann_block, reason='too_old', age_s=round(now - ann_ts, 1))
        return
    log('order', account=account, order_type=order_type, keeper_fee_sat=keeper_fee, ann_block=ann_block,
        ann_ts=ann_ts, executable_at=exec_at, seen_s_after_announce=round(now - ann_ts, 2))
    from_addr = owner() if MODE == 'live' else PAPER_OWNER
    exec_addr = EXEC if MODE == 'live' else PAPER_EXEC
    code = None if MODE == 'live' else RUNTIME
    eth_usd = eth_ref_usd()
    base_fee = int(rpc('eth_gasPrice', []), 16)     # read during the wait, not after it
    time.sleep(max(0.0, exec_at - time.time()))
    tries, last_err, outcome = 0, None, 'not_takeable'
    while tries < MAX_TRIES and time.time() < exec_at + TRY_FOR:   # tries = relay simulations
        try:
            pub, _, blob = hermes(FEED_WBTC, True)
        except Exception as e:
            last_err = 'hermes: ' + str(e)[:160]
            time.sleep(TRY_GAP)
            continue
        if pub < exec_at:                        # the module wants publishTime >= executableAt
            last_err = f'pyth update older than executableAt by {exec_at - pub} s'
            time.sleep(0.2)                      # costs no relay read; bounded by TRY_FOR
            continue
        tries += 1
        try:
            gain, gas_limit, estimated = sim_and_estimate(calldata(account, blob, 1), from_addr, exec_addr, code)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            last_err = str(e)[:220]
            if '1bed8430' in last_err:           # OrderInvalid: already executed (or cancelled)
                outcome = 'taken_before_sim'
                break
            time.sleep(TRY_GAP)
            continue
        t_sim = time.time()
        # fee cap: gasLimit x maxFeePerGas <= 90% of the simulated gross and < SEND_CAP_USD
        fee_cap = int(SEND_CAP_USD / eth_usd * 1e18 / gas_limit)
        max_fee = min(fee_cap, int(gain * GROSS_SHARE / gas_limit))
        priority = max(0, min(int(gain * BID_SHARE / gas_limit), max_fee - base_fee))
        gas_cap_wei = gas_limit * max_fee
        gas_cap_usd = gas_cap_wei / 1e18 * eth_usd
        gross_usd = gain / 1e18 * eth_usd        # same ETH reference as the cap, so the two compare
        if gas_limit > GAS_HARD_MAX or max_fee < base_fee * 11 // 10 or gas_cap_usd >= 1.0 or gain <= gas_cap_wei:
            log('opportunity_skip', account=account, gain_wei=gain, gross_usd=gross_usd, gas_limit=gas_limit,
                max_fee=max_fee, base_fee=base_fee, gas_cap_usd=gas_cap_usd, reason='gross_not_above_gas_cap')
            outcome = 'skipped'
            break
        min_profit = gas_cap_wei                 # the tx reverts unless the fee sale covers its gas cap
        data = calldata(account, blob, min_profit)
        log('opportunity', account=account, keeper_fee_sat=keeper_fee, gain_wei=gain, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, gas_estimated=estimated, max_fee=max_fee,
            priority=priority, base_fee=base_fee, eth_usd=eth_usd, min_profit=min_profit, pyth_publish=pub,
            sim_s_after_executable=round(t_sim - exec_at, 2), tries=tries, mode=MODE)
        if MODE == 'live':
            send_live(account, data, gas_limit, max_fee, priority, gain, ann_block, exec_at)
            outcome = 'sent'
        else:
            log('paper_sim', account=account, result='success', gain_wei=gain,
                sim_s_after_executable=round(t_sim - exec_at, 2))
            outcome = 'paper_success'
        break
    if outcome in ('not_takeable', 'taken_before_sim', 'paper_success'):
        # who took it and when (paper: would the simulated send have been in time?)
        if outcome == 'paper_success':
            time.sleep(8)
        try:
            win = taker(account, ann_block)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            win = {'error': str(e)[:120]}
        log('order_result', account=account, outcome=outcome, tries=tries, last_error=last_err, winner=win,
            executable_at=exec_at,
            winner_s_after_executable=(win['block_ts'] - exec_at if win and win.get('block_ts') else None))


def parse(x):
    d = x['data'][2:]
    return '0x' + d[24:64], int(d[64:128], 16), int(d[128:192], 16)


def block_ts(x):
    ts = x.get('blockTimestamp')
    if ts not in (None, '0x0', 0):
        return int(ts, 16) if isinstance(ts, str) else int(ts)
    return int(rpc('eth_getBlockByNumber', [x['blockNumber'], False])['timestamp'], 16)


def process(s, logs):
    for x in sorted(logs, key=lambda z: int(z['blockNumber'], 16)):
        if x.get('removed') or len(x.get('data', '')) < 2 + 3 * 64:
            continue
        account, order_type, fee = parse(x)
        handle(s, account, order_type, fee, int(x['blockNumber'], 16), block_ts(x))


def reread(s, label):
    """Relay read of the announcements that can still be live (the last ~70 s)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': ANN, 'fromBlock': hex(head - LOOKBACK_BLOCKS), 'toBlock': 'latest',
                               'topics': [T_ANNOUNCED]}])
    log('reread', label=label, head=head, announced=len(logs))
    s['last_poll'] = time.time()
    process(s, logs)


def feed_wait(cursor):
    q = {'address': ANN, 'topic0': T_ANNOUNCED, 'timeout': '55'}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(f'{FEED}/logs/{CHAIN}?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def load_state():
    try:
        s = json.loads(STATE.read_text())
        s.setdefault('done', {})
        return s
    except Exception:
        return {'feed_cursor': None, 'last_poll': 0, 'done': {}}


def save_state(s):
    now = time.time()
    s['done'] = {k: t for k, t in s['done'].items() if now - t < 3600}
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def main():
    s = load_state()
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, hermes=HERMES)
    try:
        pub, px, blob = hermes(FEED_WBTC, True)
        log('hermes_ok', publish_lag_s=round(time.time() - pub, 2), wbtc_usd=px, update_bytes=len(blob),
            eth_ref_usd=eth_ref_usd())
    except Exception as e:
        log('hermes_error', error=str(e)[:200])
    while True:
        try:
            if time.time() - s['last_poll'] >= SAFETY_POLL:
                reread(s, 'safety_poll')
            save_state(s)
            result = feed_wait(s.get('feed_cursor'))
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            if result.get('gap') or any(x.get('removed') for x in result.get('logs', [])):
                reread(s, 'gap')
            elif result.get('logs'):
                log('feed', events=len(result['logs']),
                    blocks=sorted({int(x['blockNumber'], 16) for x in result['logs']}))
                process(s, result['logs'])
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])
            try:
                reread(s, 'gap')
            except Exception as e2:
                log('reread_error', error=str(e2)[:180])
            time.sleep(5)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
