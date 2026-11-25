#!/usr/bin/env python3
"""trial-mycelium-v2-arbitrum

Tracer / Mycelium Perpetual Pools on Arbitrum: PoolKeeper.performUpkeepSinglePool(pool) is public and pays its caller
in the pool's quote token (USDC.e) once pool.intervalPassed() (lastPriceTimestamp + updateInterval, every 12 hours). The due
second is known 12 hours ahead, so this bot sleeps on a timer, simulates the take for the due second about 20 s before it
(eth_call with a block-time override), and in live mode sends a small burst of executor calls around the due second
with no priority fee. The executor (UpkeepTake) reverts NotDue when it is early or late and NoProfit unless the bot
wallet's USDC grew by minOut, so a lost send costs gas only (about 34,000 gas). BOT_MODE=paper sends nothing.
Confirmed chain data only: no pending transactions are read.
"""
import datetime
import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

sys.path.append('/opt/farm/lib')   # farmbot_signer lives here; the live service does not add it

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'arbitrum'
CFG = json.loads((HERE / 'config.json').read_text())

KEEPER = CFG['keeper']
POOL = CFG['pool']
PAY_TOKEN = CFG['pay_token']
SWAP_POOL = CFG['swap_pool']
USDC = CFG['usdc']
WETH = CFG['weth']
PRICE_POOL = CFG['eth_usdc_price_pool']
OFFSETS = [float(x) for x in os.environ.get('SEND_OFFSETS_S', CFG['send_offsets_s']).split(',')]
PREP_S = CFG['prep_seconds']
MAX_FEE_WEI = CFG['max_fee_wei']
GAS_CAP = CFG['gas_limit_cap']
MAX_CAP_USD = CFG['max_cap_usd']
RELAY_CU_CAP = CFG['relay_cu_cap_per_day']

EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR is required in live mode')
PAPER_OWNER = CFG['paper_owner']          # the owner baked into the paper runtime (fork deployment), paper mode only
PAPER_SIM_AT = CFG['paper_sim_address']   # where the paper runtime is placed by an eth_call code override, paper mode only
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()

SEL_RUN = '0x0523fa1e'        # cast sig "run(address,address,address,address,address,uint256)"
SEL_LAST = '0x7de93f93'       # lastPriceTimestamp()
SEL_INTERVAL = '0xfd2c80ae'   # updateInterval()
SEL_TOKEN0 = '0x0dfe1681'
SEL_TOKEN1 = '0xd21220a7'
SEL_SLOT0 = '0x3850c7bd'
ERR_NOPROFIT = '0xd4989a94'   # NoProfit(uint256)
ERR_NOTDUE = '0x47a2375f'
ERR_NOPAY = '0x5ad453ca'
TOPIC_PAID = '0xf03012dd4aab142682aa01439f94e975e2ec77ef558352323bc05f382f74b082'  # KeeperPaid(address,address,uint256)

CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_blockNumber': 10, 'eth_getBlockByNumber': 16, 'eth_estimateGas': 87,
           'eth_getTransactionReceipt': 15}
LOG = HERE / 'logs' / 'bot.jsonl'
CU_FILE = HERE / 'state' / 'cu.json'
BIAS_FILE = HERE / 'state' / 'bias.json'
_lock = threading.Lock()


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': round(time.time(), 3), 'ev': ev, **kw}
    with _lock:
        with LOG.open('a') as f:
            f.write(json.dumps(row, separators=(',', ':'), default=str) + '\n')


def rpc_raw(method, params):
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
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def rpc(method, params):
    ans = rpc_raw(method, params)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:200]}')
    return ans['result']


def word(x):
    return (x[2:] if isinstance(x, str) else '%x' % x).lower().rjust(64, '0')


def call_int(to, sel):
    return int(rpc('eth_call', [{'to': to, 'data': sel}, 'latest']), 16)


def call_addr(to, sel):
    return '0x' + rpc('eth_call', [{'to': to, 'data': sel}, 'latest'])[-40:]


def run_calldata(min_out):
    return SEL_RUN + word(KEEPER) + word(POOL) + word(PAY_TOKEN) + word(SWAP_POOL) + word(USDC) + word(min_out)


def bot_address():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a.get('address') if isinstance(a, dict) else a   # my_address() returns {"ok":..., "address":...}
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def exec_ctx():
    """(from, executor, state override) for simulations"""
    if MODE == 'live':
        return bot_address(), EXEC, {}
    return PAPER_OWNER, PAPER_SIM_AT, {PAPER_SIM_AT: {'code': RUNTIME}, PAPER_OWNER: {'balance': hex(10**18)}}


def simulate(ctx, at_ts):
    """The take as it would run in a block with timestamp at_ts. Returns (gain in USDC units or None, why, gas estimate)."""
    frm, ex, override = ctx
    tx = {'from': frm, 'to': ex, 'data': run_calldata(2**255), 'gas': hex(GAS_CAP)}
    ans = rpc_raw('eth_call', [tx, 'latest', override, {'time': hex(at_ts)}])
    data = (ans.get('error') or {}).get('data') or ''
    if not isinstance(data, str) or not data.startswith(ERR_NOPROFIT):
        why = {ERR_NOTDUE: 'not_due', ERR_NOPAY: 'no_pay'}.get(data[:10] if isinstance(data, str) else '', 'revert')
        return None, f'{why}:{str(ans.get("error") or ans.get("result"))[:160]}', None
    gain = int(data[10:74], 16)
    if gain == 0:
        return None, 'zero_gain', None
    tx = dict(tx, data=run_calldata(1))
    del tx['gas']
    est = rpc_raw('eth_estimateGas', [tx, 'latest', override, {'time': hex(at_ts)}])
    if 'error' in est:
        return gain, f'estimate_failed:{str(est["error"])[:160]}', None
    return gain, 'ok', int(est['result'], 16)


def eth_usd():
    """USDC per ETH from the Uniswap V3 WETH/USDC pool's slot0 (token0 WETH 18 dec, token1 USDC 6 dec)."""
    sq = int(rpc('eth_call', [{'to': PRICE_POOL, 'data': SEL_SLOT0}, 'latest'])[2:66], 16)
    return sq * sq * 10**12 / 2**192


def load_bias():
    try:
        return float(json.loads(BIAS_FILE.read_text())['bias_s'])
    except Exception:
        return 0.0


def sleep_to_utc_midnight():
    now = datetime.datetime.now(datetime.timezone.utc)
    tomorrow = (now + datetime.timedelta(days=1)).date()
    until = datetime.datetime.combine(tomorrow, datetime.time(), datetime.timezone.utc)
    return max(60.0, (until - now).total_seconds() + 2.0)


def live_send(at, data, gas_limit, max_fee, out, i):
    import farmbot_signer
    delay = at - time.time()
    if delay > 0:
        time.sleep(delay)
    t0 = time.time()
    try:
        reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=0)
    except Exception as ex:
        reply = {'ok': False, 'error': f'{type(ex).__name__}: {str(ex)[:200]}'}
    t1 = time.time()
    h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash') if isinstance(reply, dict) else None
    out[i] = {'i': i, 'planned': round(at, 3), 'sent': round(t0, 3), 'signer_s': round(t1 - t0, 3), 'hash': h,
              'ok': bool(isinstance(reply, dict) and reply.get('ok')), 'reply': str(reply)[:300]}
    log('send', executor=EXEC, **out[i])


def find_winner(from_block):
    logs = rpc('eth_getLogs', [{'address': KEEPER, 'fromBlock': hex(from_block), 'toBlock': 'latest',
                                'topics': [TOPIC_PAID, '0x' + word(POOL)]}])
    if not logs:
        return None
    l = logs[0]
    blk = rpc('eth_getBlockByNumber', [l['blockNumber'], False])
    return {'tx': l['transactionHash'], 'block': int(l['blockNumber'], 16), 'index': int(l['transactionIndex'], 16),
            'block_ts': int(blk['timestamp'], 16), 'paid_to': '0x' + l['topics'][2][-40:], 'reward_units': int(l['data'], 16)}


def window(ctx, due, overdue):
    """One upkeep: simulate, decide, (live) send, then record who won."""
    head = int(rpc('eth_blockNumber', []), 16)
    at_ts = max(due, int(time.time()) + 1) if overdue else due
    gain, why, est = simulate(ctx, at_ts)
    if gain is None or est is None:
        log('skip', due=due, overdue=overdue, reason=why, gain_units=gain)
        return False
    base = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    price = eth_usd()
    max_fee = base * 2 + 1
    gas_limit = min(GAS_CAP, est * 14 // 10)
    cap_usd = gas_limit * max_fee * price / 1e18
    gross_usd = gain / 1e6
    min_out = int(cap_usd * 1e6) + 1
    row = {'due': due, 'overdue': overdue, 'sim_ts': at_ts, 'gain_usdc': gross_usd, 'gas_estimate': est, 'gas_limit': gas_limit,
           'base_fee_wei': base, 'max_fee_wei': max_fee, 'eth_usd': round(price, 2), 'gas_cap_usd': round(cap_usd, 5),
           'min_out_units': min_out, 'head': head}
    log('opportunity', **row)
    refuse = None
    if max_fee > MAX_FEE_WEI:
        refuse = 'base_fee_above_max'
    elif est * 14 // 10 > GAS_CAP:
        refuse = 'gas_above_cap'
    elif cap_usd > MAX_CAP_USD:
        refuse = 'gas_cap_usd_above_max'
    elif gross_usd <= cap_usd:
        refuse = 'gross_not_above_gas_cap'
    if refuse:
        log('skip', due=due, reason=refuse, **{k: row[k] for k in ('gain_usdc', 'gas_cap_usd', 'max_fee_wei')})
        return False
    bias = load_bias()
    offsets = [0.0] if overdue else [o + bias for o in OFFSETS]
    sends = {}
    if MODE == 'live':
        data = run_calldata(min_out)
        threads = []
        start = time.time() + 0.05 if overdue else due
        for i, off in enumerate(offsets):
            t = threading.Thread(target=live_send, args=(start + off, data, gas_limit, max_fee, sends, i), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(90)
    else:
        log('paper_sim', result='success', note='eth_call at the due second with a block-time override; nothing sent',
            would_send_at=[round(due + o, 3) for o in offsets], **{k: row[k] for k in ('due', 'gain_usdc', 'gas_estimate', 'gas_cap_usd')})
    wait = due + 12 - time.time()
    if wait > 0:
        time.sleep(wait)
    winner = None
    for _ in range(3):
        winner = find_winner(head)
        if winner:
            break
        time.sleep(10)
    log('window_result', due=due, winner=winner, delay_s=(winner['block_ts'] - due) if winner else None)
    if MODE != 'live':
        return True
    early = late = won = 0
    for i in sorted(sends):
        s = sends[i]
        if not s['hash']:
            continue
        rc = None
        for _ in range(5):
            rc = rpc('eth_getTransactionReceipt', [s['hash']])
            if rc:
                break
            time.sleep(4)
        if not rc:
            log('send_result', i=i, hash=s['hash'], result='no_receipt')
            continue
        blk, idx, ok = int(rc['blockNumber'], 16), int(rc['transactionIndex'], 16), rc['status'] == '0x1'
        cost = int(rc['gasUsed'], 16) * int(rc['effectiveGasPrice'], 16)
        pos = None
        if winner and not ok:
            pos = 'early' if (blk, idx) < (winner['block'], winner['index']) else 'late'
            early += pos == 'early'
            late += pos == 'late'
        won += ok
        log('send_result', i=i, hash=s['hash'], result='won' if ok else 'lost', block=blk, index=idx, gas_used=int(rc['gasUsed'], 16),
            cost_wei=cost, cost_usd=round(cost * price / 1e18, 5), position=pos, winner_block=winner['block'] if winner else None,
            winner_index=winner['index'] if winner else None, blocks_from_winner=(blk - winner['block']) if winner else None)
    if not overdue and not won and (early or late) and not (early and late):
        new = max(-2.0, min(1.0, bias + (0.1 if early else -0.1)))   # all sends early: shift later; all late: shift earlier
        BIAS_FILE.write_text(json.dumps({'bias_s': round(new, 3)}))
        log('bias', old=bias, new=round(new, 3), early=early, late=late)
    return True


def main():
    LOG.parent.mkdir(exist_ok=True)
    CU_FILE.parent.mkdir(exist_ok=True)
    ctx = None
    interval = None
    last_overdue_try = 0.0
    while True:
        delay = 600
        try:
            if ctx is None:
                ctx = exec_ctx()
                t0, t1 = call_addr(SWAP_POOL, SEL_TOKEN0).lower(), call_addr(SWAP_POOL, SEL_TOKEN1).lower()
                if {t0, t1} != {PAY_TOKEN.lower(), USDC.lower()}:
                    raise SystemExit(f'swap pool tokens {t0} {t1} are not pay token / USDC')
                if call_addr(PRICE_POOL, SEL_TOKEN0).lower() != WETH.lower() or call_addr(PRICE_POOL, SEL_TOKEN1).lower() != USDC.lower():
                    raise SystemExit('price pool is not WETH/USDC')
                interval = call_int(POOL, SEL_INTERVAL)
                log('start', mode=MODE, executor=ctx[1], wallet=ctx[0], keeper=KEEPER, pool=POOL, interval=interval, offsets=OFFSETS,
                    bias=load_bias())
            due = call_int(POOL, SEL_LAST) + interval
            now = time.time()
            if now < due - PREP_S:
                delay = min(due - PREP_S - now, 600)
                log('wait', due=due, sleep_s=round(delay, 1))
            elif now <= due - 3:
                window(ctx, due, False)
                delay = 5
            elif now < due + 3:
                delay = 3      # too close to prepare; the next loop treats it as overdue if nobody took it
            elif now - last_overdue_try > 30:
                last_overdue_try = now
                window(ctx, due, True)   # nobody took it at the due second: take it now (the reward grows with lateness)
                delay = 5
            else:
                delay = 10
        except ReadBudgetExceeded as ex:
            log('read_budget', err=str(ex))
            delay = sleep_to_utc_midnight()
        except Exception as ex:
            log('error', err=f'{type(ex).__name__}: {str(ex)[:300]}')
            delay = 30
        time.sleep(max(1.0, delay))


if __name__ == '__main__':
    main()
