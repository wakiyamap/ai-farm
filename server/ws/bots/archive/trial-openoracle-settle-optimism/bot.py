"""trial-openoracle-settle-optimism: settler reward of OpenOracle reports on OP Mainnet, one executor call each.

OpenOracle.settle(reportId) is open to anyone once the report's settlement time has passed and pays the report's
settlerReward (ETH) to the caller. The time is known as soon as the report is submitted: InitialReportSubmitted
carries the settlement time, and the feed delivers that event about 1 s after its block. The bot waits on the feed
for that event, and for each report sends executor.settle(oracle, [id], minProfit) timed for the first eligible
block (BOT_MODE=live), or simulates the same call right after that block (BOT_MODE=paper). The executor reverts
unless its ETH balance grows by minProfit, so a lost attempt costs gas only.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.append('/opt/farm/lib')   # farmbot_signer lives here; the live service does not add it

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'optimism'
FEED = 'http://127.0.0.1:8546/logs/optimism'

# OpenOracle (verified, src/OpenOracleL1.sol), address from the explorer; nextReportId() answers there.
ORACLE = '0xf3cce3274c32f1f344ba48336d5eff34dc6e145f'
# InitialReportSubmitted(uint256,address,uint256,uint256,address,address,uint256,uint256,uint256,uint256,uint256,
#                        bool,address,bytes4,bool,uint256,bytes32,uint256)   (cast keccak; seen in receipt 0xa205becf...)
T_REPORT = '0x820b2beedf2c18d30de3d9c50bb9d50342008711b3b12587677c30711b286bea'
SEL_SETTLE = '0x987bab30'       # executor settle(address,uint256[],uint256)   (cast sig)
SEL_META = '0xff57143b'         # reportMeta(uint256)
SEL_STATUS = '0xbbbea052'       # reportStatus(uint256)
BLOCK_SECONDS = 2               # OP Mainnet block time; due blocks are derived from the report's own block

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000451'
EXEC = os.environ.get('EXECUTOR_ADDR_OPTIMISM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_OPTIMISM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip() if (HERE / 'executor-runtime.hex').exists() else ''
if MODE != 'live' and (not RUNTIME.startswith('0x') or len(RUNTIME) < 100):
    raise SystemExit('missing paper executor runtime')

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

# ---- loss guard -----------------------------------------------------------------------------
MAX_CAP_WEI = 300_000_000_000        # 3e-7 ETH: the signed gas cap of one send never exceeds this (under 0.01 USD)
MAX_FEE_WEI = 5_000_000              # 0.005 gwei absolute ceiling for maxFeePerGas
BASE_GAS = 220_000                   # fork: settle through the executor uses about 135,000-145,000 gas
MAX_CALLBACK_GAS = 300_000           # reports with a larger settlement callback are skipped
L1_ALLOWANCE_WEI = 20_000_000_000    # 2e-8 ETH; incumbents pay about 5e-9 ETH all in (L1 fee included)
TIP_WEI = 300_000                    # incumbent 0x609c8738 bids 1,000 wei
BID_SHARE = 0.25                     # priority fee x gasLimit never exceeds this share of the reward
# live: send this long before the due block's timestamp. The feed delivers a block's logs 0.13 s after its timestamp,
# so the block with timestamp T is filled from about T - 1.9 s to T + 0.1 s: a send at T - 1.6 s arrives early in that
# window (it matters if the sequencer orders by arrival) and never in the window of the block before.
SEND_LEAD_S = 1.6
PAPER_LAG_S = 2.0                    # paper: simulate this long after the due block's timestamp
MAX_AGE_S = 120                      # a report older than this past its due time is dropped, not chased
SAFETY_POLL = 600
FEED_BACKOFF_S = 30                  # feed pause after a feed error; 60 from the 11th error in a row (re-read covers 60 s)
# seconds between the receipt looks of one send (after the first look at +2.5 s); after the last: not_included
RECEIPT_DELAYS = [1.5, 1.5, 1.5, 3, 10, 30, 120, 600, 3600]
RELAY_CU_CAP = 70_000                # per UTC day; the feed's own CU is metered separately
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10,
           'eth_getBlockByNumber': 20}
_id = 0


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': round(time.time(), 3), 'ev': ev, **kw}
    with LOG.open('a') as f:
        f.write(json.dumps(row, separators=(',', ':'), default=str) + '\n')


def rpc(method, params):
    global _id
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(CU_FILE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    cost = CU_COST.get(method, 26)
    if budget['cu'] + cost > RELAY_CU_CAP:
        raise ReadBudgetExceeded(f'{RELAY_CU_CAP} relay CU/day bot cap reached')
    budget['cu'] += cost
    CU_FILE.write_text(json.dumps(budget))
    _id += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:300]}')
    return ans['result']


def word(n):
    return format(n, '064x')


def aword(a):
    return a.lower().removeprefix('0x').zfill(64)


def words(h):
    h = h.removeprefix('0x')
    return [int(h[i:i + 64], 16) for i in range(0, len(h), 64)]


def settle_calldata(ids, min_profit):
    # settle(address oracle, uint256[] ids, uint256 minProfitWei): head = oracle, offset 0x60, minProfit; tail = ids
    return SEL_SETTLE + aword(ORACLE) + word(0x60) + word(min_profit) + word(len(ids)) + ''.join(word(i) for i in ids)


def parse_report(lg):
    """One InitialReportSubmitted log -> the report's due time. Data words: reporter, amount1, amount2, swapFee,
    protocolFee, settlementTime, disputeDelay, escalationHalt, timeType, callbackContract, callbackSelector,
    trackDisputes, callbackGasLimit, stateHash, blockTimestamp."""
    w = words(lg['data'])
    if len(w) < 15 or len(lg['topics']) < 2:
        return None
    rid = int(lg['topics'][1], 16)
    b0 = int(lg['blockNumber'], 16)
    ts0, st, time_type = w[14], w[5], bool(w[8])
    if time_type:
        due_ts = ts0 + st
        due_block = b0 + -(-st // BLOCK_SECONDS)
    else:
        due_block = b0 + st
        due_ts = ts0 + st * BLOCK_SECONDS
    return {'id': rid, 'b0': b0, 'ts0': ts0, 'settlement_time': st, 'time_type': time_type, 'due_ts': due_ts,
            'due_block': due_block, 'callback': w[9] != 0 and w[10] != 0,
            # settle() makes the callback only when both the contract and the selector are set
            'callback_gas': w[12] if (w[9] != 0 and w[10] != 0) else 0, 'seen': round(time.time(), 3)}


def bot_address():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a.get('address') if isinstance(a, dict) else a   # my_address() returns {"ok":..., "address":...}
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def settler_reward(rid):
    w = words(rpc('eth_call', [{'to': ORACLE, 'data': SEL_META + word(rid)}, 'latest']))
    return w[3] if len(w) >= 12 else 0      # ReportMeta word 3 = settlerReward


def report_status(rid):
    w = words(rpc('eth_call', [{'to': ORACLE, 'data': SEL_STATUS + word(rid)}, 'latest']))
    if len(w) < 10:
        return None
    return {'report_timestamp': w[4], 'settlement_timestamp': w[5], 'distributed': bool(w[9])}


def base_fee(s):
    if time.time() - s.get('base_fee_at', 0) > 300:
        s['base_fee'] = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
        s['base_fee_at'] = time.time()
    return s['base_fee']


def plan(s, rep, reward):
    """Gas limit, fees and the guard for one settle. Returns None (and logs why) when the send is not worth it."""
    gas_limit = BASE_GAS + rep['callback_gas'] * 65 // 63
    tip = max(1, min(TIP_WEI, int(reward * BID_SHARE / gas_limit)))      # bid <= BID_SHARE of the reward
    max_fee = base_fee(s) * 2 + tip
    cap_wei = gas_limit * max_fee + L1_ALLOWANCE_WEI
    row = {'id': rep['id'], 'reward_wei': reward, 'gas_limit': gas_limit, 'max_fee': max_fee, 'priority': tip,
           'gas_cap_wei': cap_wei, 'due_block': rep['due_block'], 'due_ts': rep['due_ts'], 'time_type': rep['time_type']}
    if rep['callback_gas'] > MAX_CALLBACK_GAS:
        log('opportunity_skip', reason='callback_gas', **row)
        return None
    if max_fee > MAX_FEE_WEI or cap_wei > MAX_CAP_WEI:
        log('opportunity_skip', reason='fee_cap', **row)
        return None
    if reward <= cap_wei:                     # expected gross must exceed this send's gas cap
        log('opportunity_skip', reason='reward_below_gas_cap', **row)
        return None
    row['min_profit_wei'] = cap_wei + 1       # a win always pays more than the signed gas cap
    return row


def winner_of(rep):
    """Where the report was settled, as a block number (None while unsettled)."""
    st = report_status(rep['id'])
    if not st or not st['distributed']:
        return None
    if rep['time_type']:
        return rep['b0'] + (st['settlement_timestamp'] - rep['ts0']) // BLOCK_SECONDS
    return st['settlement_timestamp']


def send_live(s, rep, p):
    import farmbot_signer
    data = settle_calldata([rep['id']], p['min_profit_wei'])
    sent_at = time.time()
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, p['gas_limit'], p['max_fee'],
                                max_priority_fee_per_gas=p['priority'])
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply, id=rep['id'])    # final, never retried
        return
    # The send stays in state['unresolved'] (saved to disk before anything else) until reconcile() has written
    # its send_result line: won / lost, gas used and the winner's block. Nothing here waits for the receipt.
    s.setdefault('unresolved', []).append({
        'hash': h, 'id': rep['id'], 'sent_at': round(sent_at, 3), 'reward_wei': p['reward_wei'],
        'b0': rep['b0'], 'ts0': rep['ts0'], 'time_type': rep['time_type'], 'due_block': rep['due_block'],
        'due_ts': rep['due_ts'], 'tries': 0, 'next_at': sent_at + 2.5})
    save_state(s)
    log('send', hash=h, executor=EXEC, sent_at=round(sent_at, 3), seconds_before_due=round(rep['due_ts'] - sent_at, 3), **p)


def record_result(u, receipt):
    """Write the send_result line of one send from its receipt. Raises (the send stays unresolved) when the
    winner's block of a lost send cannot be read yet."""
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee') or '0x0', 16)
    wb = b if status else winner_of(u)      # None = the report is still unsettled (the send was early)
    log('send_result', hash=u['hash'], id=u['id'], result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=cost, reward_wei=u['reward_wei'], net_wei=(u['reward_wei'] - cost if status else -cost),
        send_block=b, due_block=u['due_block'], blocks_after_due=b - u['due_block'], winner_block=wb,
        winner_blocks_after_due=(wb - u['due_block'] if wb is not None else None),
        seconds_to_result=round(time.time() - u['sent_at'], 1),
        reason=None if status else ('early' if b < u['due_block'] else ('unsettled' if wb is None else 'taken')))


def reconcile(s):
    """Look up the receipt of every unresolved send that is due for a look. A send leaves the list only after its
    send_result line is written: from the receipt, or, after the last look (about 73 min after the send), as
    lost / not_included with the block where the report was settled. ReadBudgetExceeded passes through with the
    list unchanged, so the look is repeated after the cap resets."""
    for u in list(s.get('unresolved', [])):
        if u['next_at'] > time.time():
            continue
        try:
            receipt = rpc('eth_getTransactionReceipt', [u['hash']])
            if receipt:
                record_result(u, receipt)
                s['unresolved'].remove(u)
            elif u['tries'] >= len(RECEIPT_DELAYS):
                wb = winner_of(u)
                log('send_result', hash=u['hash'], id=u['id'], result='lost', reason='not_included', gas_used=0,
                    gas_cost_wei=0, reward_wei=u['reward_wei'], net_wei=0, send_block=None,
                    due_block=u['due_block'], winner_block=wb,
                    winner_blocks_after_due=(wb - u['due_block'] if wb is not None else None),
                    seconds_to_result=round(time.time() - u['sent_at'], 1))
                s['unresolved'].remove(u)
            else:
                u['next_at'] = time.time() + RECEIPT_DELAYS[u['tries']]
                u['tries'] += 1
        except ReadBudgetExceeded:
            save_state(s)
            raise
        except Exception as e:      # relay error: the same look again in 30 s, not counted as a look
            u['next_at'] = time.time() + 30
            log('reconcile_error', hash=u['hash'], error=str(e)[:180])
        save_state(s)


def sim_paper(rep, p):
    data = settle_calldata([rep['id']], p['min_profit_wei'])
    params = [{'from': PAPER_OWNER, 'to': PAPER_EXEC, 'data': data, 'gas': hex(p['gas_limit'])}, 'latest',
              {PAPER_EXEC: {'code': RUNTIME}}]
    lag = round(time.time() - rep['due_ts'], 3)
    try:
        gained = int(rpc('eth_call', params)[2:66], 16)
    except ReadBudgetExceeded:
        raise
    except RuntimeError as e:
        # executor revert: NoProfit(0) = the report was settled in its first eligible block(s) by someone else
        log('paper_sim', result='revert', seconds_after_due=lag, error=str(e)[:120], **p)
        return
    log('paper_sim', result='success', seconds_after_due=lag, gross_wei=gained,
        net_wei_at_cap=gained - p['gas_cap_wei'], **p)


def handle(s, rep):
    late = time.time() - rep['due_ts']
    if late > MAX_AGE_S:
        log('report_dropped', id=rep['id'], seconds_after_due=round(late, 1))
        return
    reward = settler_reward(rep['id'])
    log('opportunity', id=rep['id'], reward_wei=reward, due_block=rep['due_block'], due_ts=rep['due_ts'],
        time_type=rep['time_type'], settlement_time=rep['settlement_time'], report_block=rep['b0'],
        feed_delay_s=round(rep['seen'] - rep['ts0'], 3), callback=rep['callback'])
    if not reward:
        return
    p = plan(s, rep, reward)
    if not p:
        return
    if MODE == 'live':
        send_live(s, rep, p)
    else:
        sim_paper(rep, p)


def act_time(rep):
    return rep['due_ts'] - SEND_LEAD_S if MODE == 'live' else rep['due_ts'] + PAPER_LAG_S


def add_logs(pending, logs, source):
    for lg in logs:
        if lg.get('removed'):
            pending.pop(int(lg['topics'][1], 16), None)     # reorg: forget it; a re-emitted log adds it again
            continue
        rep = parse_report(lg)
        if rep and rep['id'] not in pending:
            rep['source'] = source
            pending[rep['id']] = rep


def reread(s, pending, why):
    """Feed gap / error / safety timer: read the last minute of reports through the relay once."""
    s['last_poll'] = time.time()
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': ORACLE, 'topics': [T_REPORT], 'fromBlock': hex(head - 30), 'toBlock': hex(head)}])
    done = set(s.get('done', []))       # report ids are not issued in report order: keep the handled ids themselves
    fresh = [lg for lg in logs if int(lg['topics'][1], 16) not in done]
    add_logs(pending, fresh, why)
    log('reread', why=why, head=head, logs=len(logs), added=len(fresh))


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {'feed_cursor': None, 'last_poll': 0, 'done': [], 'unresolved': []}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def feed_wait(cursor, timeout):
    q = {'address': ORACLE, 'topic0': T_REPORT, 'timeout': str(timeout)}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=timeout + 10) as r:
        return json.load(r)


def main():
    s = load_state()
    s.setdefault('unresolved', [])
    pending = {}
    feed_retry_at = 0.0
    feed_errors = 0
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), oracle=ORACLE,
        send_lead_s=SEND_LEAD_S, safety_poll_seconds=SAFETY_POLL, unresolved=len(s['unresolved']))
    while True:
        try:
            # every relay read sits inside this try: rpc() checks the daily CU cap before each read and the
            # cap error is caught below
            now = time.time()
            for rid in sorted(pending, key=lambda r: act_time(pending[r])):
                if act_time(pending[rid]) <= time.time():
                    rep = pending.pop(rid)
                    s['done'] = (s.get('done', []) + [rid])[-300:]
                    handle(s, rep)
            reconcile(s)
            if s.get('reread_owed'):
                # owed after a feed gap or ANY feed error (429 / 503 / timeout): no timing condition. It stays
                # owed until the relay read has succeeded.
                reread(s, pending, s['reread_owed'])
                s['reread_owed'] = None
                continue                    # serve what the re-read found before anything else
            if now - s.get('last_poll', 0) >= SAFETY_POLL:
                reread(s, pending, 'timer')
            save_state(s)
            wake = [act_time(r) for r in pending.values()] + [u['next_at'] for u in s['unresolved']]
            nxt = min(wake, default=None)
            if nxt is not None and nxt - time.time() < 1.0:
                time.sleep(max(0.0, nxt - time.time()))
                continue
            if time.time() < feed_retry_at:
                # the feed is paused after an error: keep serving due reports and receipts, do not call the feed
                until = feed_retry_at if nxt is None else min(nxt, feed_retry_at)
                time.sleep(max(0.0, min(until - time.time(), 30)))
                continue
            timeout = 25 if nxt is None else max(1, min(25, int(nxt - time.time())))
            try:
                result = feed_wait(s.get('feed_cursor'), timeout)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as e:
                # 429 / 503 / timeout / bad body: always re-read the oracle through the relay, on the next pass
                # (at once), whatever the time since the last poll. Only the feed itself is paused.
                feed_errors += 1
                feed_retry_at = time.time() + (FEED_BACKOFF_S if feed_errors <= 10 else 2 * FEED_BACKOFF_S)
                s['reread_owed'] = 'feed_error'
                log('feed_error', error=str(e)[:180], errors_in_row=feed_errors)
                continue
            feed_errors = 0
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            add_logs(pending, result.get('logs') or [], 'feed')
            if result.get('gap'):
                s['reread_owed'] = 'gap'
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            pending.clear()
            save_state(s)                   # unresolved sends and an owed re-read stay in the state file
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            nxt_day = (now_dt + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
            time.sleep(max(60, (nxt_day - now_dt).total_seconds()))
        except Exception as e:              # relay errors included; an owed re-read is retried on the next pass
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
