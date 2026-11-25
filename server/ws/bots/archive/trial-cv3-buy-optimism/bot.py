#!/usr/bin/env python3
"""Trial: Compound v3 cUSDCv3 + cUSDTv3 (OP Mainnet) collateral-reserve residue buys through
Cv3FlashBuyOut.

After anyone absorbs an underwater account the collateral sits in the comet's reserves and
anyone may buyCollateral() it at the comet's discount. The executor flash-swaps on a UniV3
{collateral, base} pool: sells exactly the quoted collateral, pays the comet from the pool's
base token, sells a USDT surplus to USDC on the UniV3 USDC/USDT pool, and sends the USDC to
the bot wallet; it reverts unless the USDC surplus exceeds minProfit. No principal. A lost
attempt costs gas only.

Waits on the farm feed for AbsorbCollateral on the two comets; on gap / 429 / 503 /
connection errors and every 10 min it re-reads the reserves through the relay (one
Multicall3 eth_call for all routed collaterals).
"""
import sys
sys.path.append("/opt/farm/lib")  # the live service does not put the signer lib on the path
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
CHAIN = 'optimism'
ZERO = '0x' + '0' * 40
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'   # Multicall3 (eth_getCode non-empty on optimism)
# comets: compound-finance/comet deployments/optimism/{usdc,usdt}/roots.json
C_USDC = '0x2e44e174f7d53f0212823acc11c01a11d58c5bcb'      # cUSDCv3, base = native USDC 0x0b2c639c..ff85
C_USDT = '0x995e394b8b2437ac8ce61ee0bc610d617962b214'      # cUSDTv3, base = USDT 0x94b008aa..8e58
USDC_USDT_POOL = '0xa73c628eaf6e283e26a7b1f8001cf186aa4c0e8e'  # UniV3 USDT/USDC 0.01%
OP = '0x4200000000000000000000000000000000000042'
WETH = '0x4200000000000000000000000000000000000006'
WBTC = '0x68f180fcce6836688e9084f035309e29bf0a2095'
WSTETH = '0x1f32b1c2345538c0c6f582fcb022739c4a194ebb'
# comet -> (out pool, {collateral: [UniV3 {collateral, base} pools to try]})
# pools = factory 0x1f98431c..f984 getPool(collateral, base, fee), read 2026-11-17 with their
# base-token balances (scratch/trial-cv3-buy-optimism/discover.py); the best simulated one is used.
MARKETS = {
    C_USDC: (ZERO, {
        WETH: ['0x1fb3cf6e48f1e7b10213e7b6d87d4c073c7fdb7b', '0xc1738d90e2e26c35784a0d3e3d8a9f795074bca4'],
        WBTC: ['0x394a9fcbab8599437d9ec4e5a4a0eb7cb1fd2f69', '0xadab76dd2dca7ae080a796f0ce86170e482afb4a'],
        OP: ['0xb533c12fb4e7b53b5524eab9b47d93ff6c7a456f'],
    }),
    C_USDT: (USDC_USDT_POOL, {
        WETH: ['0xc858a329bf053be78d6239c4a4343b8fbd21472b'],
        WBTC: ['0x0843e0f56b9e7fdc4fb95fabba22a01ef4088f41'],
        OP: ['0xb2ac2e5a3684411254d58b1c5a542212b782114d'],
        WSTETH: ['0x95d7d146ae40d4822c2750276b54b6eed530d374'],
    }),
}
ROUTES = [(c, coll) for c, (_, m) in MARKETS.items() for coll in m]
# cast keccak "AbsorbCollateral(address,address,address,uint256,uint256)"; same hash as the
# ledger source compound_v3.absorb and the live Base bot
T_ABSORB = '0x9850ab1af75177e4a9201c65a2cf7976d5d28e40ef63494b44366f86b2f9412e'
T_BUY = '0xf891b2a411b0e66a5f0a6ff1368670fefa287a13f541eb633a386a1a9cc7046b'     # BuyCollateral
SEL_BUY = '0xafe51de3'        # buy(address,address,address,uint256,uint256,address)
SEL_RESERVES = '0x9ff567f8'   # getCollateralReserves(address)
SEL_QUOTE = '0x7ac88ed1'      # quoteCollateral(address,uint256)
SEL_AGG3 = '0x82ad56cb'       # aggregate3((address,bool,bytes)[])
PAPER_EXEC = '0xfe00ddfee1423e3dba3e07a1b0f78b0ac1df8e9a'   # fork deployment; no code on mainnet
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000002'  # owner baked into that runtime
EXEC = os.environ.get('EXECUTOR_ADDR_OPTIMISM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_OPTIMISM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

# ---- loss guard (trial rule: every send's gas cap < 1 USD) ----
MAX_GAS_LIMIT = 900_000        # fork: success 317,964 / 339,581 / 422,048 (USDT route), estimate up to 527,933
SEND_CAP_USD = 0.95            # every send: gasLimit x maxFeePerGas x ETH price + L1 allowance <= this
L1_ALLOW_USD = 0.02            # OP Stack L1 data fee; measured 6e9-3e10 wei (< 0.0001 USD) on the incumbents
ETH_REF_MIN_USD = 2500.0       # floor of the ETH price used for the cap
ETH_REF_MARGIN = 1.15          # ETH price used = max(floor, 1.15 x the price the comet quotes WETH at)
BID_SHARE = 0.25               # priority fee bid is at most 25% of simulated gross
_eth_ref = {'usd': 4000.0}     # set by every check() from the comet's own WETH quote; 4000 until then
MIN_RESERVE_USD = 0.30         # below this the gross cannot cover gas
BUY_SHARE = 0.995              # buy this share of the reserve (quote rounding headroom)
SAFETY_POLL = 600
SEND_COOLDOWN = 30
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 10, 'eth_estimateGas': 26}
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


def multicall(calls):
    """aggregate3 with allowFailure; calls = [(target, data_hex)]; returns [int or None]."""
    n = len(calls)
    elems, offs, pos = [], [], n * 32
    for target, data in calls:
        raw = data.removeprefix('0x')
        blen = len(raw) // 2
        enc = aw(target) + word(1) + word(0x60) + word(blen) + raw.ljust(((blen + 31) // 32) * 64, '0')
        offs.append(word(pos))
        pos += len(enc) // 2
        elems.append(enc)
    data = SEL_AGG3 + word(0x20) + word(n) + ''.join(offs) + ''.join(elems)
    out = bytes.fromhex(rpc('eth_call', [{'to': MULTICALL, 'data': data}, 'latest'])[2:])
    arr = 32                                  # start of the array (its length word)
    if int.from_bytes(out[arr:arr + 32], 'big') != n:
        raise RuntimeError('multicall: bad result length')
    res = []
    for i in range(n):
        o = arr + 32 + int.from_bytes(out[arr + 32 + 32 * i: arr + 64 + 32 * i], 'big')
        ok = int.from_bytes(out[o:o + 32], 'big')
        blen = int.from_bytes(out[o + 64:o + 96], 'big')
        res.append(int.from_bytes(out[o + 96:o + 128], 'big') if ok and blen >= 32 else None)
    return res


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


def calldata(comet, coll, pool, pay, min_profit):
    return (SEL_BUY + aw(comet) + aw(coll) + aw(pool) + word(pay) + word(min_profit)
            + aw(MARKETS[comet][0]))


def call_params(data, from_addr, exec_addr, code, gas=None):
    tx = {'from': from_addr, 'to': exec_addr, 'data': data}
    if gas:
        tx['gas'] = hex(gas)
    return [tx, 'latest'] + ([{exec_addr: {'code': code}}] if code else [])


def sim(data, from_addr, exec_addr, code):
    """eth_call of the exact executor call; returns the USDC it would send to the owner."""
    return int(rpc('eth_call', call_params(data, from_addr, exec_addr, code, MAX_GAS_LIMIT)), 16)


def winner_block(comet, coll, send_block, our_hash):
    """Block of the BuyCollateral that took this collateral around our send (ours if we won)."""
    lo = max(0, send_block - 200)
    hi = max(send_block, int(rpc('eth_blockNumber', []), 16))
    logs = rpc('eth_getLogs', [{'address': comet, 'fromBlock': hex(lo), 'toBlock': hex(hi),
                               'topics': [T_BUY, None, '0x' + aw(coll)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours)
    return min((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(comet, coll, data, gas_limit, max_fee, priority, gross_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', comet=comet, collateral=coll, reply=reply)  # final: no retry
        return
    receipt = None
    for _ in range(20):  # OP Mainnet blocks are 2 s; give up after 20 s
        time.sleep(1.0)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, comet=comet, collateral=coll, result='unknown', gas_used=None,
            winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    price = int(receipt['effectiveGasPrice'], 16)
    try:
        winner = winner_block(comet, coll, b, h)
    except Exception:
        winner = None
    log('send_result', hash=h, comet=comet, collateral=coll, result='won' if status else 'lost',
        gas_used=used, gas_cost_wei=used * price, winner_block=winner, send_block=b,
        blocks_after_winner=(b - winner if winner is not None else None), gross_usd=gross_usd)


def attempt(s, comet, coll, reserve, usd, why):
    now = time.time()
    key = comet + ':' + coll
    if s['cooldown'].get(key, 0) > now:
        return
    from_addr = owner() if MODE == 'live' else PAPER_OWNER
    exec_addr = EXEC if MODE == 'live' else PAPER_EXEC
    code = None if MODE == 'live' else RUNTIME
    best, err, pay = None, None, 0
    # whole lot first; a lot too big for the pool (slippage eats the discount) is retried smaller
    for share in (BUY_SHARE, 0.5, 0.2):
        pay = int(usd * share * 1e6)
        for pool in MARKETS[comet][1][coll]:
            try:
                gain = sim(calldata(comet, coll, pool, pay, 1), from_addr, exec_addr, code)
            except ReadBudgetExceeded:
                raise
            except Exception as e:
                err = str(e)[:200]  # NoProfit (discount below fee + slippage), NotForSale, already bought
                continue
            if best is None or gain > best[1]:
                best = (pool, gain)
        if best is not None or usd * share < 20:
            break
    if best is None:
        log('simulate_revert', comet=comet, collateral=coll, why=why, reserve=reserve, reserve_usd=usd,
            pay=pay, error=err)
        return
    pool, gain = best
    gross_usd = gain / 1e6          # the executor pays out USDC (6 decimals)
    try:
        # L2 execution gas only; the OP Stack L1 data fee is charged apart (L1_ALLOW_USD)
        est = int(rpc('eth_estimateGas', call_params(calldata(comet, coll, pool, pay, 1), from_addr,
                                                     exec_addr, code)), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', comet=comet, collateral=coll, why=why, stage='estimateGas', error=str(e)[:200])
        return
    gas_limit = (est * 5 + 3) // 4
    base_fee = int(rpc('eth_gasPrice', []), 16)
    eth_usd = _eth_ref['usd']
    # hard fee cap for this send: gasLimit x maxFee x ETH price + L1 allowance <= SEND_CAP_USD
    fee_cap = int((SEND_CAP_USD - L1_ALLOW_USD) / eth_usd * 1e18 / gas_limit)
    priority = int(gross_usd * BID_SHARE / eth_usd * 1e18 / gas_limit)
    max_fee = min(fee_cap, base_fee * 2 + priority)
    priority = min(priority, max(0, max_fee - base_fee))
    gas_cap_usd = gas_limit * max_fee / 1e18 * eth_usd + L1_ALLOW_USD
    # trial send rule: expected gross must exceed this send's gas cap
    if gas_limit > MAX_GAS_LIMIT or max_fee < base_fee or gas_cap_usd >= 1.0 or gross_usd <= gas_cap_usd:
        log('opportunity_skip', comet=comet, collateral=coll, why=why, reserve_usd=usd, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, base_fee=base_fee, eth_usd=eth_usd,
            reason='gross_not_above_gas_cap')
        return
    min_profit = int(gas_cap_usd * 1e6)
    data = calldata(comet, coll, pool, pay, min_profit)
    try:
        gain = sim(data, from_addr, exec_addr, code)  # the exact bytes to send
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', comet=comet, collateral=coll, why=why, reserve_usd=usd, pay=pay,
            error=str(e)[:200])
        return
    log('opportunity', comet=comet, collateral=coll, pool=pool, why=why, reserve=reserve, reserve_usd=usd,
        pay=pay, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, max_fee=max_fee,
        priority=priority, simulated_gain=gain, mode=MODE)
    s['cooldown'][key] = now + SEND_COOLDOWN
    if MODE == 'live':
        send_live(comet, coll, data, gas_limit, max_fee, priority, gross_usd)
    else:
        log('paper_sim', comet=comet, collateral=coll, result='success', gain=gain)


def check(s, why):
    """One Multicall3 read of every routed collateral's reserve and quote; try what is worth trying."""
    calls = []
    for comet, coll in ROUTES:
        calls.append((comet, SEL_RESERVES + aw(coll)))
        calls.append((comet, SEL_QUOTE + aw(coll) + word(10**6)))
    res = multicall(calls)
    # ETH price for the per-send cap, from the comet's own quote: WETH wei sold per 1 USDC
    weth_q = res[2 * ROUTES.index((C_USDC, WETH)) + 1]
    if not weth_q:
        raise RuntimeError('no WETH quote from cUSDCv3: cannot price gas, nothing is tried')
    _eth_ref['usd'] = max(ETH_REF_MIN_USD, ETH_REF_MARGIN * 1e18 / weth_q)
    rows = {}
    for i, (comet, coll) in enumerate(ROUTES):
        reserve, per_usd = res[2 * i], res[2 * i + 1]
        usd = reserve / per_usd if reserve and per_usd else 0.0
        rows[comet[:8] + ':' + coll[:6] + coll[-4:]] = round(usd, 4)  # OP and WETH share a prefix
        if usd >= MIN_RESERVE_USD:
            attempt(s, comet, coll, reserve, usd, why)
    log('check', why=why, reserve_usd=rows, eth_usd=round(_eth_ref['usd'], 2))


def feed_wait(cursor):
    q = {'address': C_USDC + ',' + C_USDT, 'topic0': T_ABSORB, 'timeout': '55'}
    if cursor:
        q['after'] = cursor   # the string cursor the feed returned; never sent on the first call
    with urllib.request.urlopen(f'{FEED}/logs/{CHAIN}?' + urllib.parse.urlencode(q, safe=','), timeout=65) as r:
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
