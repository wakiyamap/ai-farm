#!/usr/bin/env python3
"""Trial: Compound v3 cUSDCv3 (Base) collateral-reserve residue buys through Cv3FlashBuy.

After anyone absorbs an underwater account the collateral sits in the comet's reserves and
anyone may buyCollateral() it at the comet's discount. The executor flash-swaps on a UniV3
pool: sells exactly the quoted collateral, pays the comet from the pool's USDC, keeps the
surplus and sends it to the bot wallet; it reverts unless the surplus exceeds minProfit.
No principal. A lost attempt costs gas only.

Waits on the farm feed for AbsorbCollateral on the comet; on gap / 429 / 503 / connection
errors and every 10 min it re-reads the reserves through the relay.
"""
import sys as _farm_sys; _farm_sys.path.append("/opt/farm/lib")  # human 2026-11-17: signer import path
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
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
FEED = os.environ.get('FEED_URL', 'http://127.0.0.1:8546')
CHAIN = 'base'
COMET = '0xb125e6687d4313864e53df431d5425969c15eb2f'   # cUSDCv3 on Base
# collateral -> UniV3 {collateral, USDC} 0.05% pool used for the flash sale
ROUTES = {
    '0x4200000000000000000000000000000000000006': '0xd0b53d9277642d899df5c87a3966a349a798f224',  # WETH
    '0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf': '0xfbb6eed8e7aa03b138556eedaf5d271a5e1e43ef',  # cbBTC
}
# cast keccak "AbsorbCollateral(address,address,address,uint256,uint256)"; seen on chain in
# tx 0x8c30d087.. (block 57502604). The first version of this bot waited on a wrong hash.
T_ABSORB = '0x9850ab1af75177e4a9201c65a2cf7976d5d28e40ef63494b44366f86b2f9412e'
T_BUY = '0xf891b2a411b0e66a5f0a6ff1368670fefa287a13f541eb633a386a1a9cc7046b'     # BuyCollateral
SEL_BUY = '0xe79c149e'        # buy(address,address,address,uint256,uint256)
SEL_RESERVES = '0x9ff567f8'   # getCollateralReserves(address)
SEL_QUOTE = '0x7ac88ed1'      # quoteCollateral(address,uint256)
PAPER_EXEC = '0xfe00ddfee1423e3dba3e07a1b0f78b0ac1df8e9a'   # fork deployment; no code on mainnet
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000002'  # owner baked into that runtime
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

# ---- loss guard (trial rule: every send's gas cap < 1 USD) ----
GAS_LIMIT = 500_000            # fork: success 344,433, NoProfit revert 400,928
MAX_FEE_WEI = 450_000_000      # 0.45 gwei hard cap: 500k x 0.45 gwei = 2.25e-4 ETH
ETH_REF_USD = 4000.0           # deliberately high ETH price: cap = 0.90 USD at 4000
L1_FEE_USD = 0.02              # allowance for the OP-stack L1 data fee of a ~200-byte tx
BID_SHARE = 0.25               # priority fee bid is at most 25% of simulated gross
MIN_RESERVE_USD = 0.30         # below this the gross cannot cover gas
BUY_SHARE = 0.995              # buy this share of the reserve (quote rounding headroom)
SAFETY_POLL = 600
SEND_COOLDOWN = 30
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 10}
CU_CAP = 60_000                # relay reads/day; the feed filter is on top
_id = 0


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
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


def load_state():
    try:
        s = json.loads(STATE.read_text())
        if isinstance(s, dict):
            s.setdefault('feed_cursor', None)
            s.setdefault('last_poll', 0)
            s.setdefault('cooldown', {})
            return s
    except Exception:
        pass
    return {'feed_cursor': None, 'last_poll': 0, 'cooldown': {}}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def owner():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a['address'] if isinstance(a, dict) else a
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def calldata(coll, pay, min_profit):
    return SEL_BUY + aw(COMET) + aw(coll) + aw(ROUTES[coll]) + word(pay) + word(min_profit)


def sim(coll, pay, min_profit, from_addr, exec_addr, code):
    """eth_call of the exact executor call; returns the USDC surplus it would send to the owner."""
    tx = {'from': from_addr, 'to': exec_addr, 'data': calldata(coll, pay, min_profit), 'gas': hex(GAS_LIMIT)}
    params = [tx, 'latest'] + ([{exec_addr: {'code': code}}] if code else [])
    return int(rpc('eth_call', params), 16)


def winner_block(coll, send_block, our_hash):
    """Block of the BuyCollateral that took this collateral around our send (ours if we won)."""
    lo = max(0, send_block - 50)
    hi = max(send_block, int(rpc('eth_blockNumber', []), 16))
    logs = rpc('eth_getLogs', [{'address': COMET, 'fromBlock': hex(lo), 'toBlock': hex(hi),
                               'topics': [T_BUY, None, '0x' + aw(coll)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours)
    return min((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(coll, data, max_fee, priority, gross_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, GAS_LIMIT, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', collateral=coll, reply=reply)  # final: no retry
        return
    receipt = None
    for _ in range(30):  # base blocks are 0.2 s; give up after 15 s
        time.sleep(0.5)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, collateral=coll, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    price = int(receipt['effectiveGasPrice'], 16)
    l1 = int(receipt.get('l1Fee') or '0x0', 16)
    try:
        winner = winner_block(coll, b, h)
    except Exception:
        winner = None
    log('send_result', hash=h, collateral=coll, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * price + l1, l1_fee_wei=l1, winner_block=winner, send_block=b,
        blocks_after_winner=(b - winner if winner is not None else None), gross_usd=gross_usd)


def attempt(s, coll, reserve, usd, why):
    now = time.time()
    if s['cooldown'].get(coll, 0) > now:
        return
    from_addr = owner() if MODE == 'live' else PAPER_OWNER
    exec_addr = EXEC if MODE == 'live' else PAPER_EXEC
    code = None if MODE == 'live' else RUNTIME
    pay = int(usd * BUY_SHARE * 1e6)
    try:
        gain = sim(coll, pay, 1, from_addr, exec_addr, code)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        # NoProfit (discount below the pool fee), NotForSale, or already bought
        log('simulate_revert', collateral=coll, why=why, reserve=reserve, reserve_usd=usd, pay=pay,
            error=str(e)[:200])
        return
    gross_usd = gain / 1e6
    base_fee = int(rpc('eth_gasPrice', []), 16)
    priority = int(gross_usd * BID_SHARE / ETH_REF_USD * 1e18 / GAS_LIMIT)
    max_fee = min(MAX_FEE_WEI, base_fee * 2 + priority)
    priority = min(priority, max_fee)
    gas_cap_usd = GAS_LIMIT * max_fee / 1e18 * ETH_REF_USD + L1_FEE_USD
    # trial send rule: expected gross must exceed this send's gas cap
    if max_fee < base_fee or gas_cap_usd >= 1.0 or gross_usd <= gas_cap_usd:
        log('opportunity_skip', collateral=coll, why=why, reserve_usd=usd, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, base_fee=base_fee, reason='gross_not_above_gas_cap')
        return
    min_profit = int(gas_cap_usd * 1e6)
    data = calldata(coll, pay, min_profit)
    try:
        gain = sim(coll, pay, min_profit, from_addr, exec_addr, code)  # the exact bytes to send
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', collateral=coll, why=why, reserve_usd=usd, pay=pay, error=str(e)[:200])
        return
    log('opportunity', collateral=coll, why=why, reserve=reserve, reserve_usd=usd, pay=pay,
        gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, max_fee=max_fee, priority=priority,
        simulated_gain=gain, mode=MODE)
    s['cooldown'][coll] = now + SEND_COOLDOWN
    if MODE == 'live':
        send_live(coll, data, max_fee, priority, gross_usd)
    else:
        log('paper_sim', collateral=coll, result='success', gain=gain)


def check(s, why):
    """Read every routed collateral's reserve through the relay and try what is worth trying."""
    rows = {}
    for coll in ROUTES:
        reserve = int(rpc('eth_call', [{'to': COMET, 'data': SEL_RESERVES + aw(coll)}, 'latest']), 16)
        usd = 0.0
        if reserve:
            per_usd = int(rpc('eth_call', [{'to': COMET, 'data': SEL_QUOTE + aw(coll) + word(10**6)}, 'latest']), 16)
            usd = reserve / per_usd if per_usd else 0.0
        rows[coll] = round(usd, 4)
        if usd >= MIN_RESERVE_USD:
            attempt(s, coll, reserve, usd, why)
    log('check', why=why, reserve_usd=rows)


def feed_wait(cursor):
    q = {'address': COMET, 'topic0': T_ABSORB, 'timeout': '55'}
    if cursor:
        q['after'] = cursor   # the string cursor the feed returned; never sent on the first call
    with urllib.request.urlopen(f'{FEED}/logs/{CHAIN}?' + urllib.parse.urlencode(q), timeout=65) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, routes=len(ROUTES))
    while True:
        now = time.time()
        try:
            if now - s['last_poll'] >= SAFETY_POLL:
                check(s, 'safety_poll')
                s['last_poll'] = now
            s['cooldown'] = {u: t for u, t in s['cooldown'].items() if t > now}
            save_state(s)
            result = feed_wait(s.get('feed_cursor'))
            if isinstance(result.get('cursor'), str):
                s['feed_cursor'] = result['cursor']
            if result.get('gap') or any(x.get('removed') for x in result.get('logs', [])):
                check(s, 'gap')
                s['last_poll'] = time.time()
            elif result.get('logs'):
                log('feed', events=len(result['logs']),
                    blocks=sorted({int(x['blockNumber'], 16) for x in result['logs']}),
                    assets=sorted({'0x' + x['topics'][3][-40:] for x in result['logs']
                                   if len(x.get('topics', [])) > 3}))
                check(s, 'absorb')
                s['last_poll'] = time.time()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            # HTTPError (429, 503, 400...) is a URLError: we may have missed an absorb, so
            # re-read the reserves through the relay, at most once a minute while the feed is down
            code = getattr(e, 'code', None)
            log('feed_error', error=str(e)[:180], code=code)
            if code == 400:
                s['feed_cursor'] = None      # cursor not accepted: subscribe afresh
            if time.time() - s.get('last_gap_check', 0) >= 60:
                s['last_gap_check'] = time.time()
                try:
                    check(s, 'gap')
                    s['last_poll'] = time.time()
                except Exception as e2:
                    log('check_error', why='gap', error=str(e2)[:180])
            time.sleep(10 if code in (429, 503) else 5)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
