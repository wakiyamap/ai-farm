#!/usr/bin/env python3
"""Sherlock V2 staking pool on ethereum: the public arbRestake(id) reward.

A staking position (NFT id) whose lockup ended more than 2 weeks ago, and whose owner neither redeemed nor restaked it,
may be restaked for 26 weeks by anyone. The caller is paid in USDC out of the position: 0 at lockupEnd + 2 weeks, growing
linearly to 20 % of the position over the next 7 days (Sherlock.sol _calcSharesForArbRestake). The start time of every
position is therefore known weeks ahead from lockupEnd(id).

The bot scans lockupEnd of all ids once a day, sleeps until a position has been in its ramp for LAG_S, simulates
SherlockArb.run(pool, USDC, ids, minProfit, deadlineBlock) with the exact bytes, and (live) sends it by the private route
when the USDC reward covers the send's gas cap. The executor reverts unless it received at least minProfit USDC and pays
all of it to the bot wallet. No principal.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', '').rstrip('/')
CHAIN = 'ethereum'

# Sherlock.sol staking pool (verified on Etherscan; KB lead 391 / attempts:3605); USDC = its token() (asserted in proof.py);
# Uniswap V3 USDC / WETH 0.05 % pool, token0 USDC, token1 WETH (asserted in proof.py), used only to price gas in USD.
POOL = '0x0865a889183039689034da55c1fd12af5083eabf'
USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
PRICE_POOL = '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640'

SEL = {  # all from `cast sig`
    'run': '0x191562c9',          # run(address,address,uint256[],uint256,uint256)
    'lockupEnd': '0xbf362cb9',    # lockupEnd(uint256)
    'viewReward': '0x07441979',   # viewRewardForArbRestake(uint256) -> (uint256 profit, bool able)
    'slot0': '0x3850c7bd',        # slot0()
}

PAPER_EXEC = '0x8f7a45ebde059392e46a46dcc14ab24681a961ea'    # fork deployment (proof.json); paper code override only
PAPER_OWNER = '0x1111111111111111111111111111111111111111'   # the owner baked into that deployment (immutable)
EXEC = os.environ.get('EXECUTOR_ADDR_ETHEREUM') or os.environ.get('EXECUTOR_ADDR')
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'

WAIT_S = 14 * 86400            # ARB_RESTAKE_WAIT_TIME
GROW_S = 7 * 86400             # ARB_RESTAKE_GROWTH_TIME
# ---- when to take ----
LAG_S = 6 * 3600               # take 6 h into the ramp: under the dust sweeper's lags (10.3 h - 55 h); id 703 went at 696 s (attempts:3627)
MAX_IDS = 12                   # ids per transaction
# ---- loss guard ----
MIN_NET_USD = 0.02             # send only if simulated USDC reward - this send's gas cap >= 0.02 USD
MIN_PROFIT_SHARE = 0.95        # executor minProfit = 95 % of the simulated reward (and never under the gas cap)
GAS_LIMIT_MAX = 2_500_000
GAS_MARGIN = 1.3
MAX_FEE_WEI = 3 * 10**9        # never sign above 3 gwei: 2.5M gas x 3 gwei = 0.0075 ETH (12.4 USD at 1,657)
PRIORITY_WEI = 10**8           # 0.1 gwei tip to the builder (private route), not a bid for anybody's order
DEADLINE_BLOCKS = 3            # executor reverts after head + 3 (private-send rule)
MAX_SENDS_DAY = 8              # sends per UTC day, whatever the results
PER_ID_GAS = 150_000          # first guess of one restake's gas, only to pre-filter ids before the simulation
# ---- timing / reads ----
SCAN_S = 86400                 # full lockupEnd scan once a day
SCAN_AHEAD = 150               # ids scanned beyond the highest live id seen (ids are sequential, 715 on 2026-11-22)
MAX_ID_START = 715
RETRY_S = 1800                 # a position in its ramp whose reward does not cover gas yet: look again in 30 min
SLEEP_MAX = 6 * 3600
CU_COST = {'eth_call': 26, 'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10, 'eth_getBlockByNumber': 20,
           'eth_estimateGas': 26}
CU_CAP = 60_000                # relay CU/day, hard cap in code
_id = 0


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    LOG.parent.mkdir(exist_ok=True)
    row = {'ts': time.time(), 'ev': ev, **kw}
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
    if budget['cu'] + cost > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} relay CU/day bot cap reached')
    budget['cu'] += cost
    CU_FILE.parent.mkdir(exist_ok=True)
    CU_FILE.write_text(json.dumps(budget))
    _id += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {ans["error"]}')
    return ans['result']


def word(n):
    return format(n, '064x')


def aw(a):
    return a.lower().removeprefix('0x').zfill(64)


def run_data(ids, min_profit, deadline_block):
    """run(address pool, address token, uint256[] ids, uint256 minProfit, uint256 deadlineBlock)"""
    return (SEL['run'] + aw(POOL) + aw(USDC) + word(0xa0) + word(min_profit) + word(deadline_block)
            + word(len(ids)) + ''.join(word(i) for i in ids))


def lockup_end(i):
    """lockupEnd(id); 0 for an id that does not exist (never minted or redeemed: the getter reverts NonExistent)."""
    try:
        return int(rpc('eth_call', [{'to': POOL, 'data': SEL['lockupEnd'] + word(i)}, 'latest'])[2:66], 16)
    except RuntimeError as e:
        if 'revert' in str(e).lower():
            return 0
        raise                                   # a relay error is not "does not exist"


def view_reward(i):
    """(USDC reward raw, able) of viewRewardForArbRestake; (0, False) if the id no longer exists."""
    try:
        r = rpc('eth_call', [{'to': POOL, 'data': SEL['viewReward'] + word(i)}, 'latest'])
    except RuntimeError as e:
        if 'revert' in str(e).lower():
            return 0, False
        raise
    return int(r[2:66], 16), bool(int(r[66:130], 16))


def eth_usd():
    sq = int(rpc('eth_call', [{'to': PRICE_POOL, 'data': SEL['slot0']}, 'latest'])[2:66], 16)
    return 1e12 / ((sq / 2**96) ** 2)        # token0 USDC (6), token1 WETH (18)


# ---------------------------------------------------------------- state

def load_state():
    try:
        st = json.loads(STATE.read_text())
    except Exception:
        st = {}
    st.setdefault('pos', {})           # id -> lockupEnd
    st.setdefault('last_scan', 0)
    st.setdefault('max_id', MAX_ID_START)
    st.setdefault('done', {})          # id -> lockupEnd of the occurrence already simulated (paper) or sent (live)
    st.setdefault('sends', 0)
    st.setdefault('wins', 0)
    return st


def save_state(st):
    STATE.parent.mkdir(exist_ok=True)
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(st))
    tmp.replace(STATE)


def scan(st):
    """lockupEnd of every id up to the highest live id + SCAN_AHEAD. Logs positions that left a ramp since the last scan."""
    now = time.time()
    old = st['pos']
    pos = {}
    top = st['max_id']
    i = 1
    while i <= top + SCAN_AHEAD:
        le = lockup_end(i)
        if le:
            pos[str(i)] = le
            top = max(top, i)
        i += 1
    for k, le in old.items():
        if le + WAIT_S <= now and pos.get(k) != le:
            # it was in its ramp and somebody restaked or redeemed it: a natural occurrence, with its lag
            log('position_left_ramp', id=int(k), old_lockup_end=le, new_lockup_end=pos.get(k), ramp_start=le + WAIT_S,
                seen_gone_after_s=int(now - le - WAIT_S))
    st['pos'], st['max_id'], st['last_scan'] = pos, top, now
    save_state(st)
    nxt = sorted((le + WAIT_S, int(k)) for k, le in pos.items() if le + WAIT_S + GROW_S > now)[:8]
    log('scan', positions=len(pos), max_id=top, in_ramp=[k for s, k in nxt if s <= now],
        next_starts=[{'id': k, 'ramp_start': s} for s, k in nxt if s > now])


# ---------------------------------------------------------------- send

def signer():
    sys.path.append('/opt/farm/lib')
    import farmbot_signer
    return farmbot_signer


def owner():
    a = signer().my_address()
    a = a['address'] if isinstance(a, dict) else a
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def ctx():
    """(from, executor, state override list) for this mode."""
    if MODE == 'live':
        return owner(), EXEC, []
    runtime = (HERE / 'executor-runtime.hex').read_text().strip()
    return PAPER_OWNER, PAPER_EXEC, [{PAPER_EXEC: {'code': runtime}}]


def send_live(ids, data, gas_limit, max_fee, deadline, sim_profit, st):
    st['sends'] += 1
    save_state(st)
    reply = signer().send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=PRIORITY_WEI)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', reply=reply, ids=ids)       # final: no retry of this request
        return
    receipt = None
    while True:
        time.sleep(4)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt or int(rpc('eth_blockNumber', []), 16) > deadline + 1:
            break
    if not receipt:
        receipt = rpc('eth_getTransactionReceipt', [h])
    if not receipt:
        log('send_result', hash=h, result='private_not_included', deadline_block=deadline, ids=ids, gas_used=None,
            winner_block=None)
        return
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    if status:
        st['wins'] += 1
        save_state(st)
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16), send_block=int(receipt['blockNumber'], 16),
        winner_block=None, simulated_profit_usdc=sim_profit / 1e6, ids=ids)


def evaluate(ready, st):
    """ready: ids at least LAG_S into their ramp. Simulate the exact bytes; send (live) or log (paper) if the USDC
    reward covers this send's gas cap. Returns True if something was sent or paper-simulated."""
    frm, ex, ov = ctx()
    head = rpc('eth_getBlockByNumber', ['latest', False])
    base_fee = int(head['baseFeePerGas'], 16)
    deadline = int(head['number'], 16) + DEADLINE_BLOCKS
    px = eth_usd()
    max_fee = min(MAX_FEE_WEI, base_fee * 3 // 2 + PRIORITY_WEI)
    if max_fee < base_fee + PRIORITY_WEI:
        log('opportunity_skip', reason='base_fee_above_cap', base_fee=base_fee, ids=ready)
        return False
    per_id_cap_usd = PER_ID_GAS * GAS_MARGIN * max_fee / 1e18 * px
    rows = []
    for i in ready:
        rew, able = view_reward(i)
        if not able:
            le = lockup_end(i)                 # restaked or redeemed by somebody since the scan
            log('position_left_ramp', id=i, old_lockup_end=st['pos'].get(str(i)), new_lockup_end=le or None)
            if le:
                st['pos'][str(i)] = le
            else:
                st['pos'].pop(str(i), None)
            save_state(st)
            continue
        rows.append((rew, i))
    rows.sort(reverse=True)
    pick = [i for rew, i in rows if rew / 1e6 >= per_id_cap_usd][:MAX_IDS]
    tag = dict(ids=pick, rewards_usdc={i: rew / 1e6 for rew, i in rows}, eth_usd=round(px, 2), base_fee=base_fee)
    if not pick:
        if rows:
            log('opportunity_skip', reason='reward_under_gas', per_id_gas_cap_usd=round(per_id_cap_usd, 4), **tag)
        return False
    call = {'from': frm, 'to': ex, 'data': run_data(pick, 1, deadline)}
    try:
        profit = int(rpc('eth_call', [call, 'latest'] + ov)[2:66], 16)
        est = int(rpc('eth_estimateGas', [call, 'latest'] + ov), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', error=str(e)[:220], **tag)
        return False
    gas_limit = min(GAS_LIMIT_MAX, int(est * GAS_MARGIN))
    gas_cap_usd = gas_limit * max_fee / 1e18 * px
    net = profit / 1e6 - gas_cap_usd
    if est > GAS_LIMIT_MAX or net < MIN_NET_USD:
        log('opportunity_skip', reason='gas_over_limit' if est > GAS_LIMIT_MAX else 'net_under_min', profit_usdc=profit / 1e6,
            gas_cap_usd=round(gas_cap_usd, 4), gas_est=est, **tag)
        return False
    min_profit = max(int(profit * MIN_PROFIT_SHARE), int(gas_cap_usd * 1e6) + 1)
    data = run_data(pick, min_profit, deadline)
    log('opportunity', profit_usdc=profit / 1e6, min_profit_usdc=min_profit / 1e6, gas_cap_usd=round(gas_cap_usd, 4), gas_est=est,
        gas_limit=gas_limit, max_fee=max_fee, deadline_block=deadline, mode=MODE,
        ramp_age_s={i: int(time.time() - st['pos'][str(i)] - WAIT_S) for i in pick}, **tag)
    for i in pick:
        st['done'][str(i)] = st['pos'][str(i)]
    save_state(st)
    if MODE == 'live':
        day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        if st.get('send_day') != day:
            st['send_day'], st['day_sends'] = day, 0
        if st['day_sends'] >= MAX_SENDS_DAY:
            log('opportunity_skip', reason='max_sends_per_day', ids=pick)
            for i in pick:
                st['done'].pop(str(i), None)
            save_state(st)
            return False
        st['day_sends'] += 1
        send_live(pick, data, gas_limit, max_fee, deadline, profit, st)
        for i in pick:                         # re-read: a win moved lockupEnd by 26 weeks; a miss leaves it for a retry
            le = lockup_end(i)
            if le == st['pos'].get(str(i)):
                st['done'].pop(str(i), None)
            elif le:
                st['pos'][str(i)] = le
        save_state(st)
    else:
        log('paper_sim', result='success', profit_usdc=profit / 1e6, gas_cap_usd=round(gas_cap_usd, 4),
            net_usd=round(profit / 1e6 - est * (base_fee + PRIORITY_WEI) / 1e18 * px, 4), gas_est=est, ids=pick)
    return True


def step(st):
    """One pass. Returns seconds to sleep."""
    now = time.time()
    if now - st['last_scan'] >= SCAN_S:
        scan(st)
    ready, wake = [], st['last_scan'] + SCAN_S
    for k, le in st['pos'].items():
        start = le + WAIT_S
        if now >= start + GROW_S + 30 * 86400:
            continue                             # stuck far past its ramp (nobody takes it: reward under gas for good)
        if st['done'].get(k) == le:
            continue                             # this occurrence was already simulated (paper) or sent and resolved
        if now >= start + LAG_S:
            ready.append(int(k))
        else:
            wake = min(wake, start + LAG_S)
    if ready:
        acted = evaluate(sorted(ready), st)
        wake = min(wake, time.time() + (60 if (acted and MODE == 'live') else RETRY_S))
    return max(30, min(SLEEP_MAX, wake - time.time()))


def main():
    if MODE == 'live' and not EXEC:
        raise SystemExit('EXECUTOR_ADDR_ETHEREUM or EXECUTOR_ADDR is required in live mode')
    if not RELAY:
        raise SystemExit('RPC_RELAY_URL is required')
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, pool=POOL, lag_s=LAG_S, cu_cap=CU_CAP)
    while True:
        try:
            st = load_state()
            pause = step(st)
            log('sleep', seconds=int(pause))
            time.sleep(pause)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            nxt = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
            time.sleep(max(60, (nxt - now).total_seconds()))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('relay_error', error=str(e)[:180])
            time.sleep(60)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(60)


if __name__ == '__main__':
    main()
