#!/usr/bin/env python3
"""trial: Silo v1 (Arbitrum) flash liquidations through an atomic executor, on a timer."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'arbitrum'
WETH = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'      # arbiscan WETH; router.WETH9() must equal it (checked at start)
ROUTER = '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45'    # Uniswap SwapRouter02 (arbiscan verified name)
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'  # Multicall3
PAPER_EXEC = '0x5110e11400000000000000000000000000000a11'
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()   # artifact deployedBytecode, owner = PAPER_OWNER
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

SEL_TAKE = '0x3e0bd9dd'        # cast sig take(address,address,address,bytes,uint256)
SEL_SOLVENT = '0x38b51ce1'     # cast sig isSolvent(address)
SEL_ASSETS = '0x67e4ac2c'      # cast sig getAssets()
SEL_AGG3 = '0x82ad56cb'        # cast sig aggregate3((address,bool,bytes)[])
SEL_GETPOOL = '0x1698ee82'     # cast sig getPool(address,address,uint24)
SEL_FACTORY = '0xc45a0155'     # cast sig factory()
SEL_WETH9 = '0x4aa4a4fc'       # cast sig WETH9()
SEL_BALANCE = '0x70a08231'     # cast sig balanceOf(address)
SEL_STORAGE = '0xbf273041'     # cast sig assetStorage(address)
SEL_PRICE = '0x41976e09'       # cast sig getPrice(address)  (PriceProvidersRepository, ETH per whole token, 1e18)
SEL_PPR = '0x5ddf2be3'         # cast sig priceProvidersRepository()
SEL_REPO = '0xbde12718'        # cast sig siloRepository()
SEL_DECIMALS = '0x313ce567'    # cast sig decimals()
T_BORROW = '0x312a5e5e1079f5dda4e95dbbd0b908b291fd5b992ef22073643ab691572c5b52'     # Borrow(address,address,uint256)
T_LIQUIDATE = '0xf3fa0eaee8f258c23b013654df25d1527f98a5c7ccd5e951dd77caca400ef972'  # Liquidate(address,address,uint256,uint256)
FEES = (500, 3000, 10000, 100)

POLL_SECONDS = 30           # per Multicall3 chunk of watched borrowers (one eth_call each); see README read cost
CHUNK = 300                 # isSolvent calls per Multicall3 eth_call
REFRESH_SECONDS = 7200      # new Borrow emitters (three eth_getLogs for the 61 silos)
REBUILD_SECONDS = 24 * 3600 # which borrowers still have debt worth watching (the watch list)
MIN_DEBT_WEI = 3 * 10**14   # 0.0003 ETH of debt: below it the liquidation margin cannot cover one send's gas
SKIP_SECONDS = 24 * 3600    # an insolvent case that does not simulate above the cap (bad debt, no route) is retried daily
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 13, 10
GAS_LIMIT_MAX = 3_000_000
MAX_FEE_WEI = 50_000_000    # 0.05 gwei: no send while base fee x 1.5 is above this
TIP_WEI = 1                 # Arbitrum orders first come first served; no priority bid
ETH_REF_USD = 5000.0        # conservative, for the <= 1 USD per send cap
MAX_TX_USD = 0.90
CU_CAP = 95_000
CU_COST = {'eth_call': 26, 'eth_getBlockByNumber': 20, 'eth_estimateGas': 20, 'eth_getLogs': 75,
           'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10}

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state'
LOG.parent.mkdir(exist_ok=True)
STATE.mkdir(exist_ok=True)
SILOS = json.loads((HERE / 'silos.json').read_text())
SEED = json.loads((HERE / 'borrowers.json').read_text())


class ReadBudgetExceeded(Exception):
    pass


def log(event, **fields):
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': round(time.time(), 3), 'ev': event, **fields}, separators=(',', ':')) + '\n')


def load(name, default):
    try:
        return json.loads((STATE / name).read_text())
    except Exception:
        return default


def save(name, obj):
    tmp = STATE / (name + '.tmp')
    tmp.write_text(json.dumps(obj))
    tmp.replace(STATE / name)


def rpc(method, params):
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    budget = load('cu.json', {'day': day, 'cu': 0})
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    budget['cu'] += CU_COST.get(method, 26)
    if budget['cu'] > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} CU/day cap')
    save('cu.json', budget)
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:300]}')
    return ans['result']


# ---- ABI helpers (no dependencies) ----
def word(n):
    return format(n, '064x')


def aw(addr):
    return addr.lower().removeprefix('0x').zfill(64)


def enc_bytes(hexstr):
    h = hexstr.removeprefix('0x')
    n = len(h) // 2
    return word(n) + h + '0' * ((64 - len(h) % 64) % 64)


def enc_array(bodies):
    """Array of dynamic elements: length, offsets (relative to the start of the offsets), bodies."""
    out, off = word(len(bodies)), 32 * len(bodies)
    for b in bodies:
        out += word(off)
        off += len(b) // 2
    return out + ''.join(bodies)


def enc_swap(router, token_in, token_out, path):
    return aw(router) + aw(token_in) + aw(token_out) + word(0x80) + enc_bytes(path)


def enc_routes(pre, post):
    a = enc_array([enc_swap(*s) for s in pre])
    b = enc_array([enc_swap(*s) for s in post])
    return word(0x40) + word(0x40 + len(a) // 2) + a + b


def take_calldata(silo, user, routes_hex, min_profit):
    return SEL_TAKE + aw(silo) + aw(user) + aw(WETH) + word(0xa0) + word(min_profit) + enc_bytes(routes_hex)


def eth_call(to, data, block='latest'):
    return rpc('eth_call', [{'to': to, 'data': data}, block])


def multicall(calls, block='latest'):
    """calls: [(target, calldata)] -> [(success, returndata hex without 0x)]"""
    bodies = [aw(t) + word(1) + word(0x60) + enc_bytes(d) for t, d in calls]
    raw = eth_call(MULTICALL, SEL_AGG3 + word(0x20) + enc_array(bodies), block)[2:]
    base = 64                                  # after the outer offset word
    n = int(raw[base:base + 64], 16)
    start = base + 64                          # offsets are relative to here
    out = []
    for i in range(n):
        off = start + 2 * int(raw[start + 64 * i:start + 64 * i + 64], 16)
        ok = int(raw[off:off + 64], 16) == 1
        doff = off + 2 * int(raw[off + 64:off + 128], 16)
        dlen = int(raw[doff:doff + 64], 16)
        out.append((ok, raw[doff + 64:doff + 64 + 2 * dlen]))
    if len(out) != len(calls):
        raise RuntimeError('multicall length mismatch')
    return out


# ---- routes: every silo asset is sold through its deepest Uniswap V3 pool against WETH ----
_factory = None
_assets = {}


def factory():
    global _factory
    if _factory is None:
        if int(eth_call(ROUTER, SEL_WETH9), 16) != int(WETH, 16):
            raise SystemExit('router WETH9 mismatch')
        _factory = '0x' + eth_call(ROUTER, SEL_FACTORY)[-40:]
    return _factory


def fee_for(token, block='latest'):
    """Fee tier of the token/WETH V3 pool holding the most WETH; 0 = no pool. Cached for a day."""
    cache = load('fees.json', {})
    hit = cache.get(token)
    if hit and block == 'latest' and time.time() - hit['ts'] < 86400:
        return hit['fee']
    pools = multicall([(factory(), SEL_GETPOOL + aw(token) + aw(WETH) + word(f)) for f in FEES], block)
    addrs = ['0x' + r[-40:] if ok and len(r) == 64 else None for ok, r in pools]
    live = [(f, a) for f, a in zip(FEES, addrs) if a and int(a, 16)]
    best, best_bal = 0, 0
    if live:
        bals = multicall([(WETH, SEL_BALANCE + aw(a)) for _, a in live], block)
        for (f, _), (ok, r) in zip(live, bals):
            b = int(r, 16) if ok and r else 0
            if b > best_bal:
                best, best_bal = f, b
    if block == 'latest':
        cache[token] = {'fee': best, 'weth': best_bal, 'ts': time.time()}
        save('fees.json', cache)
    return best


def silo_assets(silo, block='latest'):
    if silo not in _assets or block != 'latest':
        raw = eth_call(silo, SEL_ASSETS, block)[2:]
        n = int(raw[64:128], 16)
        got = ['0x' + raw[128 + 64 * i:192 + 64 * i][-40:] for i in range(n)]
        if block != 'latest':
            return got
        _assets[silo] = got
    return _assets[silo]


def build_routes(silo, block='latest'):
    """pre: buy each owed asset with each other asset (the executor skips what is not owed or not held);
    post: sell every non-WETH asset that is left to WETH."""
    fees = {}
    for a in silo_assets(silo, block):
        if a == WETH:
            fees[a] = None
        else:
            f = fee_for(a, block)
            if f:
                fees[a] = f
    hop = lambda t: t[2:] + format(fees[t], '06x')     # token + its fee towards WETH
    pre, post = [], []
    for d in fees:              # debt asset to buy
        for c in fees:          # collateral to sell
            if c == d:
                continue
            if c == WETH:
                path = '0x' + hop(d) + WETH[2:]
            elif d == WETH:
                path = '0x' + WETH[2:] + format(fees[c], '06x') + c[2:]
            else:
                path = '0x' + hop(d) + WETH[2:] + format(fees[c], '06x') + c[2:]
            pre.append((ROUTER, c, d, path))
    for c in fees:
        if c != WETH:
            post.append((ROUTER, c, WETH, '0x' + hop(c) + WETH[2:]))
    return enc_routes(pre, post), sorted(a for a in silo_assets(silo, block) if a not in fees)


# ---- executor calls ----
def owner():
    import farmbot_signer
    result = farmbot_signer.my_address()
    address = result['address'] if isinstance(result, dict) else result
    if not isinstance(address, str) or len(address) != 42:
        raise RuntimeError('signer my_address returned no address')
    return address


def call_params(data, gas_limit=None, block='latest'):
    address = EXEC if MODE == 'live' else PAPER_EXEC
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': address, 'data': data}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx, block]
    if MODE == 'paper':
        params.append({address: {'code': RUNTIME}})
    return params


def winner_of(silo, user, from_block):
    """Block and tx of the Liquidate event that took this borrower (ours or a rival's)."""
    logs = rpc('eth_getLogs', [{'address': silo, 'fromBlock': hex(from_block), 'toBlock': 'latest',
                                'topics': [T_LIQUIDATE, None, '0x' + aw(user)]}])
    if not logs:
        return None, None
    return int(logs[0]['blockNumber'], 16), logs[0]['transactionHash']


def send_live(silo, user, data, gain, cap, max_fee, gas_limit, seen_block):
    import farmbot_signer
    # The signer turns a tip of 0 into maxFee/10, so the tip is always passed explicitly.
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=TIP_WEI)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', silo=silo, user=user, reply=reply)
        return
    receipt = None
    for _ in range(40):
        time.sleep(0.5)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=tx_hash, result='unknown', silo=silo, user=user, expected_gross_wei=gain,
            cap_wei=cap, gas_limit=gas_limit, max_fee_wei=max_fee, gas_used=None, winner_block=None)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        wblock, wtx = winner_of(silo, user, seen_block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        wblock, wtx = None, None
    log('send_result', hash=tx_hash, result='won' if status else 'lost', silo=silo, user=user,
        gas_used=used, gas_limit=gas_limit, max_fee_wei=max_fee, cap_wei=cap, gas_cost_wei=cost,
        expected_gross_wei=gain, net_wei=(gain - cost) if status else -cost, send_block=block,
        winner_block=wblock, winner_tx=wtx, seen_block=seen_block,
        blocks_after_winner=(block - wblock) if wblock is not None else None)


def evaluate(silo, user, block='latest', seen_block=0):
    """Simulate the take for one insolvent borrower; send (live) or log (paper) when gross > the signed gas cap."""
    routes, unrouted = build_routes(silo, block)
    if unrouted:
        log('opportunity_skip', reason='unrouted_silo_asset', silo=silo, user=user,
            unrouted=unrouted, block=block)
        return None
    data1 = take_calldata(silo, user, routes, 1)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(data1, None, block)), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', silo=silo, user=user, unrouted=unrouted, error=str(e)[:240])
        return None
    gas_limit = estimate * GAS_MARGIN_NUM // GAS_MARGIN_DEN
    base_fee = int(rpc('eth_getBlockByNumber', [block, False])['baseFeePerGas'], 16)
    max_fee = base_fee * 3 // 2 + TIP_WEI
    cap = gas_limit * max_fee
    try:
        gain = int(rpc('eth_call', call_params(data1, gas_limit, block)), 16)
    except Exception as e:
        log('simulate_revert', step='call', silo=silo, user=user, gas_limit=gas_limit, error=str(e)[:240])
        return None
    row = dict(silo=silo, user=user, gross_wei=gain, cap_wei=cap, base_fee=base_fee, max_fee_wei=max_fee,
               gas_estimate=estimate, gas_limit=gas_limit, unrouted=unrouted, block=block)
    log('opportunity', **row)
    if max_fee > MAX_FEE_WEI or gas_limit > GAS_LIMIT_MAX or cap / 1e18 * ETH_REF_USD >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', **row)
        return row
    if gain <= cap:
        log('opportunity_skip', reason='gross_not_above_signed_gas_cap', **row)
        return row
    data = take_calldata(silo, user, routes, cap + 1)       # the transaction reverts unless gain > its gas cap
    try:
        checked = int(rpc('eth_call', call_params(data, gas_limit, block)), 16)
    except Exception as e:
        log('simulate_revert', step='guarded', silo=silo, user=user, error=str(e)[:240])
        return row
    if checked <= cap:
        return row
    row['would_send'] = True
    if MODE == 'paper' or block != 'latest':
        log('paper_sim', result='success', **row)
    else:
        send_live(silo, user, data, checked, cap, max_fee, gas_limit, seen_block)
    return row


def refresh_borrowers(book, head):
    """Add new Borrow emitters since the last scan (three eth_getLogs for the 61 silos)."""
    lo = book['scanned_to'] + 1
    added = []
    if lo > head:
        return added
    for i in range(0, len(SILOS), 24):
        logs = rpc('eth_getLogs', [{'address': SILOS[i:i + 24], 'topics': [T_BORROW],
                                    'fromBlock': hex(lo), 'toBlock': hex(head)}])
        for l in logs:
            s, u = l['address'].lower(), '0x' + l['topics'][2][-40:]
            if u not in book['borrowers'].setdefault(s, []):
                book['borrowers'][s].append(u)
                added.append((s, u))
    book['scanned_to'] = head
    save('borrowers.json', book)
    if added:
        log('borrowers_added', count=len(added), to_block=head)
    return added


def rebuild_watch(book, block='latest'):
    """Watch list = (silo, user) pairs whose debt is worth at least MIN_DEBT_WEI of ETH at the silo's own oracle
    price (debt share balance x getPrice / 10^decimals; shares are within interest of amounts)."""
    silos = [s for s, us in book['borrowers'].items() if us]
    repos = ['0x' + r[-40:] for ok, r in multicall([(s, SEL_REPO) for s in silos], block)]
    uniq = sorted(set(repos))
    pprs = dict(zip(uniq, ['0x' + r[-40:] for ok, r in multicall([(r, SEL_PPR) for r in uniq], block)]))
    ppr = {s: pprs[r] for s, r in zip(silos, repos)}
    q = [(s, a) for s in silos for a in silo_assets(s, block)]
    debt_tokens = {}            # silo -> [(debt token, ETH price of one whole asset token, decimals)]
    for i in range(0, len(q), 50):
        part = q[i:i + 50]
        calls = []
        for s, a in part:
            calls += [(s, SEL_STORAGE + aw(a)), (ppr[s], SEL_PRICE + aw(a)), (a, SEL_DECIMALS)]
        res = multicall(calls, block)
        for k, (s, a) in enumerate(part):
            (ok1, st), (ok2, pr), (ok3, dec) = res[3 * k:3 * k + 3]
            if ok1 and ok2 and ok3 and len(st) >= 192 and len(pr) == 64 and len(dec) == 64:
                debt_tokens.setdefault(s, []).append(('0x' + st[128:192][-40:], int(pr, 16), int(dec, 16)))
    calls = [(s, u, t, pr, dec) for s in silos for u in book['borrowers'][s] for t, pr, dec in debt_tokens.get(s, [])]
    value = {}
    for i in range(0, len(calls), 300):
        part = calls[i:i + 300]
        res = multicall([(c[2], SEL_BALANCE + aw(c[1])) for c in part], block)
        for (s, u, _, pr, dec), (ok, r) in zip(part, res):
            if ok and r and int(r, 16) > 0:
                value[(s, u)] = value.get((s, u), 0) + int(r, 16) * pr // 10 ** dec
    out = sorted(k for k, v in value.items() if v >= MIN_DEBT_WEI)
    if block == 'latest':
        save('watch.json', {'ts': time.time(), 'pairs': out})
        log('watch_rebuilt', pairs_book=sum(len(v) for v in book['borrowers'].values()), with_debt=len(value),
            watched=len(out), min_debt_wei=MIN_DEBT_WEI)
    return out


def insolvent_pairs(pairs, block='latest'):
    bad = []
    for i in range(0, len(pairs), CHUNK):
        part = pairs[i:i + CHUNK]
        res = multicall([(s, SEL_SOLVENT + aw(u)) for s, u in part], block)
        for (s, u), (ok, r) in zip(part, res):
            if ok and len(r) == 64 and int(r, 16) == 0:
                bad.append((s, u))
    return bad


_last_bad = None


def check(watch):
    global _last_bad
    bad = insolvent_pairs(watch)
    if bad != _last_bad:
        log('insolvent', watched=len(watch), count=len(bad), pairs=bad[:40])
        _last_bad = bad
    skip = load('skip.json', {})
    todo = [(s, u) for s, u in bad if skip.get(s + u, 0) <= time.time()]
    if not todo:
        return len(bad)
    head = int(rpc('eth_blockNumber', []), 16)
    for silo, user in todo:
        row = evaluate(silo, user, 'latest', head)
        if not row or not row.get('would_send'):
            skip[silo + user] = time.time() + SKIP_SECONDS    # below the cap or reverting: retried daily
    save('skip.json', {k: v for k, v in skip.items() if v > time.time()})
    return len(bad)


def main():
    book = load('borrowers.json', None) or SEED
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, silos=len(SILOS),
        pairs=sum(len(v) for v in book['borrowers'].values()), poll_seconds=POLL_SECONDS)
    watch, refreshed, rebuilt, beat = [], 0.0, 0.0, 0.0
    while True:
        started = time.monotonic()
        try:
            now = time.time()
            if now - refreshed > REFRESH_SECONDS:
                new = refresh_borrowers(book, int(rpc('eth_blockNumber', []), 16))
                refreshed = now
                watch += [p for p in new if p not in watch]     # a new borrower is watched at once, whatever its size
            if now - rebuilt > REBUILD_SECONDS:
                watch = [tuple(p) for p in rebuild_watch(book)]
                rebuilt = now
            bad = check(watch)
            if now - beat > 3600:
                log('check', watched=len(watch), insolvent=bad, cu_today=load('cu.json', {}).get('cu'))
                beat = now
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(3600)
        except Exception as e:
            log('check_error', error=str(e)[:300])
        chunks = max(1, -(-len(watch) // CHUNK))
        time.sleep(max(1, POLL_SECONDS * chunks - (time.monotonic() - started)))


if __name__ == '__main__':
    main()
