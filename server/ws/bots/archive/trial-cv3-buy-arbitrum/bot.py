#!/usr/bin/env python3
"""Trial: Compound v3 cUSDCv3 + cUSDTv3 (Arbitrum) collateral-reserve residue buys through
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
CHAIN = 'arbitrum'
ZERO = '0x' + '0' * 40
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'   # Multicall3
C_USDC = '0x9c4ec768c28520b50860ea7a15bd7213a9ff58bf'      # cUSDCv3, base = native USDC
C_USDT = '0xd98be00b5d27fc98112bde293e487f8d4ca57d07'      # cUSDTv3, base = USDT
USDC_USDT_POOL = '0xbe3ad6a5669dc0b8b12febc03608860c31e2eef6'  # UniV3 USDC/USDT 0.01%
ARB = '0x912ce59144191c1204e64559fe8253a0e49e6548'
WETH = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'
WBTC = '0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f'
WSTETH = '0x5979d7b546e38e414f7e9822514be443a4800529'
GMX = '0xfc5a1a6eb076a2c7ad06ed22c90d7e710e35ad0a'
# comet -> (out pool, {collateral: [UniV3 {collateral, base} pools to try]})
# pools = factory 0x1f98431c..f984 getPool(collateral, base, fee), read 2026-11-17
# (scratch/trial-cv3-buy-arbitrum/discover.py); the best simulated one is used.
MARKETS = {
    C_USDC: (ZERO, {
        WETH: ['0xc6962004f452be9203591991d15f6b388e09e8d0'],
        WBTC: ['0x0e4831319a50228b9e450861297ab92dee15b44f'],
        WSTETH: ['0x7092e723285fe1381a3a59c0d438f53d2c26d9e8', '0xab007665a4dfd24830f0ca19206f9fbd7c3aa85f'],
        ARB: ['0xaebdca1bc8d89177ebe2308d62af5e74885dccc3', '0xb0f6ca40411360c03d41c5ffc5f179b8403cdcf8'],
        GMX: ['0x135e49cc315fed87f989e072ee11132686cf84f3'],
    }),
    C_USDT: (USDC_USDT_POOL, {
        WETH: ['0x641c00a822e8b671738d32a431a4fb6074e5c79d'],
        WBTC: ['0x5969efdde3cf5c0d9a88ae51e47d721096a97203'],
        WSTETH: ['0x90ac0bdbe01ff0e0699c1c9e9a089493d8a349b3', '0x83f1f0913f1352d052be6ceea4f4913ddf52a28a'],
        ARB: ['0x97bca422ec0ee4851f2110ea743c1cd0a14835a1', '0xb791ad21ba45c76629003b4a2f04c0d544406e37'],
        GMX: ['0x9e91dd7e538a7424841902a14fbe42ebf99e9a7e'],
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

# ---- loss guard (trial rule: every send's gas cap < 1 USD) ----
MAX_GAS_LIMIT = 1_200_000      # fork: success 412,231 / 331,946; Nitro adds an L1 part to the estimate
MAX_FEE_WEI = 200_000_000      # 0.2 gwei hard cap (base fee is ~0.02 gwei)
ETH_REF_USD = 4000.0           # deliberately high ETH price: 1.2M x 0.2 gwei x 4000 = 0.96 USD
BID_SHARE = 0.25               # priority fee bid is at most 25% of simulated gross
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
    for _ in range(30):  # arbitrum blocks are 0.25 s; give up after 15 s
        time.sleep(0.5)
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
    pay = int(usd * BUY_SHARE * 1e6)
    best, err = None, None
    for pool in MARKETS[comet][1][coll]:
        try:
            gain = sim(calldata(comet, coll, pool, pay, 1), from_addr, exec_addr, code)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            err = str(e)[:200]      # NoProfit (discount below the pool fee), NotForSale, already bought
            continue
        if best is None or gain > best[1]:
            best = (pool, gain)
    if best is None:
        log('simulate_revert', comet=comet, collateral=coll, why=why, reserve=reserve, reserve_usd=usd,
            pay=pay, error=err)
        return
    pool, gain = best
    gross_usd = gain / 1e6          # the executor pays out USDC (6 decimals)
    try:
        # Nitro: the gas limit comes from eth_estimateGas (it includes the L1 data part)
        est = int(rpc('eth_estimateGas', call_params(calldata(comet, coll, pool, pay, 1), from_addr,
                                                     exec_addr, code)), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', comet=comet, collateral=coll, why=why, stage='estimateGas', error=str(e)[:200])
        return
    gas_limit = (est * 5 + 3) // 4
    base_fee = int(rpc('eth_gasPrice', []), 16)
    priority = int(gross_usd * BID_SHARE / ETH_REF_USD * 1e18 / gas_limit)
    max_fee = min(MAX_FEE_WEI, base_fee * 2 + priority)
    priority = min(priority, max(0, max_fee - base_fee))
    gas_cap_usd = gas_limit * max_fee / 1e18 * ETH_REF_USD
    # trial send rule: expected gross must exceed this send's gas cap
    if gas_limit > MAX_GAS_LIMIT or max_fee < base_fee or gas_cap_usd >= 1.0 or gross_usd <= gas_cap_usd:
        log('opportunity_skip', comet=comet, collateral=coll, why=why, reserve_usd=usd, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, gas_limit=gas_limit, base_fee=base_fee, reason='gross_not_above_gas_cap')
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
    rows = {}
    for i, (comet, coll) in enumerate(ROUTES):
        reserve, per_usd = res[2 * i], res[2 * i + 1]
        usd = reserve / per_usd if reserve and per_usd else 0.0
        rows[comet[:8] + ':' + coll[:8]] = round(usd, 4)
        if usd >= MIN_RESERVE_USD:
            attempt(s, comet, coll, reserve, usd, why)
    log('check', why=why, reserve_usd=rows)


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
