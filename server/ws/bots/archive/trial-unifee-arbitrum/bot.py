#!/usr/bin/env python3
"""trial-unifee-arbitrum: flash-funded Uniswap fee release on Arbitrum One.

Anyone may pay the Releaser a fixed 2000 UNI and receive the whole TokenJar balance of up to 20 assets
(Uniswap/protocol-fees ExchangeReleaser.release). The bot simulates, on a timer, one executor transaction:
Morpho WETH flash loan -> buy 2000 UNI (UniV3) -> permissionless V3 fee collects into the jar -> release ->
sell the released assets to WETH (UniV3) -> repay. It sends only when the simulated gain exceeds the gas cap.
The pool list of the collects and the asset list are copied from the latest public release transaction.
"""
import datetime
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.append("/opt/farm/lib")  # live service does not put the signer library on the path

HERE = pathlib.Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545').rstrip('/')
CHAIN = 'arbitrum'
FEED = 'http://127.0.0.1:8546/logs/arbitrum'
LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'

# Addresses: Uniswap/protocol-fees README (Releaser, TokenJar), read back on-chain (RESOURCE(), TOKEN_JAR(),
# threshold()); Morpho Blue from the incumbent's flash-loan trace and KB lead 255; SwapRouter02 confirmed by
# factory() and WETH9(); the V3 fee adapter is read from factory.owner() at start, never typed.
RELEASER = '0xb8018422bce25d82e70cb98fda96a4f502d89427'
JAR = '0x95e337c5b155385945d407f5396387d0c2a3a263'
UNI = '0xfa7f8980b0f1e64a2062791cc3b0871572f1f7f0'
WETH = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'
USDC = '0xaf88d065e77c8cc2239327c5edb3a432268e5831'
MORPHO = '0x6c247b1f6182318877311737bac0844baa518f5e'
ROUTER = '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45'
FACTORY = '0x1f98431c8ad98523631ae4a59f267346ea31f984'
POOL_MANAGER = '0x360e68faccca8ca495c1b759fd9eee466db9fb32'   # Uniswap v4 PoolManager (incumbent trace; protocolFeeController() answers)
LINK = '0xf97f4df75117a78c1a5a0dbb814af92458539fb4'           # only as a hop of one UNI purchase leg (incumbent's venue)
USDT = '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9'
WBTC = '0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f'
HUBS = (USDC, USDT, WBTC)                                     # second-hop hubs the incumbents sell through
QUOTER = '0x61ffe014ba17989e743c5f6cb21bf9697530b21e'         # Uniswap QuoterV2 (factory() and WETH9() answer); eth_call only
LENS_GAS = 45_000_000
LENS_ADDR = '0x00000000000000000000000000000000000f1e15'      # no contract there: code override address of the read-only lens
LENS_RUNTIME = (HERE / 'lens-runtime.hex').read_text().strip() if (HERE / 'lens-runtime.hex').exists() else None
NATIVE = '0x0000000000000000000000000000000000000000'       # v4 native-ETH fees: released as native, counted as gain
RELEASED_TOPIC = '0x0143172ff1dd87f3691e870b3fb5616db820278d26d2d16c3e03330a240a6c38'

SEL_RUN = '0x2472f7dc'          # run(address,address,uint256,(address,uint256,bytes,address,uint256)[],uint256)
SEL_RELEASE = 'f7af5470'        # release(uint256,address[],address)
SEL_COLLECT_V3 = 'd7ee9368'     # V3 fee adapter collect((pool,uint128,uint128)[]) (shape copied from a public release)
SEL_COLLECT_V4 = 'e0511234'     # V4 fee adapter collect (calldata copied verbatim from a public release)
SEL_EXACT_OUT = '09b81346'      # exactOutput((bytes,address,uint256,uint256))
SEL_PROBE = '0x236b220c'        # FeeLens.probe((address,bytes)[],address,address[]) (eth_call with code override only)
SEL_TOKENS_OF = '0x346c91a9'    # FeeLens.tokensOf(address[])
SEL_BEST_ROUTES = '0x9fac9fbe'  # FeeLens.bestRoutes(address,bytes[],uint256[],uint256)
SEL_FEE_CONTROLLER = '0xf02de3b2'        # PoolManager.protocolFeeController()
SEL_EXACT_IN = 'b858183f'       # exactInput((bytes,address,uint256,uint256))
SEL_APPROVE = '095ea7b3'
SEL_DEPOSIT = 'd0e30db0'
SEL_NONCE = '0xaffed0e0'
SEL_THRESHOLD = '0x42cde4e8'
SEL_GETPOOL = '0x1698ee82'
SEL_BALANCEOF = '0x70a08231'
SEL_OWNER = '0x8da5cb5b'
SEL_SLOT0 = '0x3850c7bd'
ERR_NOPROFIT = '0x31708d59'     # cast sig NoProfit(uint256,uint256)

PAPER = json.loads((HERE / 'paper-exec.json').read_text()) if (HERE / 'paper-exec.json').exists() else {}
PAPER_EXEC = PAPER.get('executor')       # fork deployment; paper code override only, never used live
PAPER_OWNER = PAPER.get('owner')
RUNTIME = PAPER.get('runtime')

EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR is required in live mode')

FLASH_WETH = 10 * 10**18         # same size as the incumbent's Morpho flash loan
SIM_FLOAT = 8 * 10**18           # native lent to the executor in the read-only distance simulation
MAX_ASSETS = 20
HISTORY = 5                      # public releases whose pool / asset lists are copied
FEES = (100, 500, 3000, 10000)
MIN_ASSET_WEI = 2 * 10**14       # assets worth less than 0.0002 WETH at spot are left in the jar
GAS_CAP_USD = 0.90               # maxFeePerGas x gasLimit of one send stays under this (manifest: 1 USD)
BID_SHARE = 0.30                 # priority fee bid: at most this share of the simulated gross
RELAY_CU_CAP = 90_000            # per UTC day
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 20, 'debug_traceTransaction': 400, 'eth_getBlockByNumber': 20}
_id = 0


class ReadBudgetExceeded(Exception):
    pass


class CallReverted(Exception):
    def __init__(self, data, msg):
        super().__init__(msg)
        self.data = data


def log(ev, **kw):
    row = {'ts': round(time.time(), 3), 'ev': ev, **kw}
    LOG.parent.mkdir(exist_ok=True)
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
    try:
        CU_FILE.parent.mkdir(exist_ok=True)
        CU_FILE.write_text(json.dumps(budget))
    except OSError:
        pass
    _id += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        err = ans['error']
        data = err.get('data') if isinstance(err, dict) else None
        if isinstance(data, dict):
            data = data.get('data')
        if isinstance(data, str) and data.startswith('0x') and method in ('eth_call', 'eth_estimateGas'):
            raise CallReverted(data, f'{method}: {str(err)[:300]}')
        raise RuntimeError(f'{method}: {str(err)[:300]}')
    return ans['result']


def word(n):
    return format(n, '064x')


def aword(a):
    return a.lower().removeprefix('0x').zfill(64)


def at(h, i):
    return int(h[2 + i * 64:2 + (i + 1) * 64], 16)


def call(to, data, block='latest'):
    return rpc('eth_call', [{'to': to, 'data': data}, block])


def enc_bytes(hexstr):
    """ABI bytes: length word + right-padded data (hex without 0x)."""
    return word(len(hexstr) // 2) + hexstr.ljust(((len(hexstr) + 63) // 64) * 64, '0')


def enc_step(target, data, bal_token=None, bal_offset=0, value=0):
    """Step tuple (address target, uint256 value, bytes data, address balToken, uint256 balOffset)."""
    return aword(target) + word(value) + word(0xa0) + aword(bal_token or '0x0') + word(bal_offset) + enc_bytes(data)


def enc_run(steps, min_profit, flash=FLASH_WETH):
    heads, tails, off = '', '', 32 * len(steps)
    for s in steps:
        heads += word(off)
        tails += s
        off += len(s) // 2
    return (SEL_RUN + aword(MORPHO) + aword(WETH) + word(flash) + word(0xa0) + word(min_profit)
            + word(len(steps)) + heads + tails)


def path_hex(parts):
    return ''.join(format(p, '06x') if isinstance(p, int) else p[2:].lower() for p in parts)


def adapters(block='latest'):
    """[V3 fee adapter = factory.owner(), V4 fee adapter = PoolManager.protocolFeeController()], read on-chain."""
    return ['0x' + call(FACTORY, SEL_OWNER, block)[-40:], '0x' + call(POOL_MANAGER, SEL_FEE_CONTROLLER, block)[-40:]]


def template_from_tx(tx_hash, adapter_list):
    """Copy from a public release transaction (callTracer): the V3 pools whose protocol fees it collected,
    its V4 collect calls and its asset list."""
    trace = rpc('debug_traceTransaction', [tx_hash, {'tracer': 'callTracer'}])
    pools, v4, assets = [], [], []

    def walk(c):
        to = (c.get('to') or '').lower()
        inp = c.get('input') or '0x'
        if to in adapter_list and c.get('type') == 'CALL' and not c.get('error'):
            if inp[2:10] == SEL_COLLECT_V3:
                body = inp[10:]
                off = int(body[0:64], 16) * 2
                n = int(body[off:off + 64], 16)
                for i in range(n):
                    w = body[off + 64 + i * 192: off + 128 + i * 192]
                    pool = '0x' + w[24:]
                    if pool not in pools:
                        pools.append(pool)
                return
            if inp[2:10] == SEL_COLLECT_V4:
                if [to, inp[2:]] not in v4:
                    v4.append([to, inp[2:]])
                return
        if to == RELEASER and inp[2:10] == SEL_RELEASE and not c.get('error'):
            body = inp[10:]
            off = int(body[64:128], 16) * 2
            n = int(body[off:off + 64], 16)
            for i in range(n):
                assets.append('0x' + body[off + 64 + i * 64 + 24: off + 128 + i * 64])
        for x in c.get('calls') or []:
            walk(x)

    walk(trace)
    return {'tx': tx_hash, 'v3_pools': pools, 'v4_calls': v4, 'assets': assets}


def union(history):
    pools, v4, assets = [], [], []
    for h in history:
        pools += [x for x in h['v3_pools'] if x not in pools]
        v4 += [x for x in h['v4_calls'] if x not in v4]
        assets += [x for x in h['assets'] if x not in assets]
    return pools, v4, assets


def collect_calls(s):
    """[(target, calldata hex)]: V3 adapter collects in chunks of 200 pools (max amounts), then the V4 calls."""
    pools, v4, _ = union(s['history'])
    m = word(2**128 - 1)
    out = []
    for i in range(0, len(pools), 200):
        chunk = pools[i:i + 200]
        out.append((s['v3_adapter'], SEL_COLLECT_V3 + word(0x20) + word(len(chunk)) + ''.join(aword(x) + m + m for x in chunk)))
    return out + [(to, d) for to, d in v4]


def lens_call(data, block='latest'):
    return rpc('eth_call', [{'to': LENS_ADDR, 'data': data, 'gas': hex(LENS_GAS)}, block,
                            {LENS_ADDR: {'code': LENS_RUNTIME}}])


def refresh_cands(s, block='latest'):
    """Candidate assets = every token of the copied V3 pools plus the copied asset lists."""
    ads = adapters(block)
    s['v3_adapter'] = ads[0]
    for h in s['history']:
        h['v4_calls'] = [x for x in h['v4_calls'] if x[0] in ads]
    pools, _, assets = union(s['history'])
    toks = [a for a in assets if a not in (WETH, NATIVE)]
    for i in range(0, len(pools), 150):
        chunk = pools[i:i + 150]
        out = lens_call(SEL_TOKENS_OF + word(0x20) + word(len(chunk)) + ''.join(aword(x) for x in chunk), block)
        for j in range(at(out, 1)):
            t = '0x' + out[2 + (2 + j) * 64 + 24: 2 + (3 + j) * 64]
            if int(t, 16) and t not in toks and t != WETH:
                toks.append(t)
    s['tokens'] = toks
    s['rate'] = {}          # sale routes are re-quoted after every release
    s['threshold'] = at(call(RELEASER, SEL_THRESHOLD, block), 0)


def probe(s, block='latest'):
    """Jar balance of every candidate after the collects, by one eth_call of the lens (code override)."""
    calls = collect_calls(s)
    tokens = [WETH, NATIVE] + s['tokens']
    heads, tails, off = '', '', 32 * len(calls)
    for to, d in calls:
        t = aword(to) + word(0x40) + enc_bytes(d)
        heads += word(off)
        tails += t
        off += len(t) // 2
    calls_enc = word(len(calls)) + heads + tails
    data = (SEL_PROBE + word(0x60) + aword(JAR) + word(0x60 + len(calls_enc) // 2) + calls_enc
            + word(len(tokens)) + ''.join(aword(t) for t in tokens))
    out = lens_call(data, block)
    n = at(out, 1)
    return {tokens[i]: at(out, 2 + i) for i in range(n)}


def sale_paths(token):
    """Candidate UniV3 sale paths to WETH: direct (4 fee tiers) and through USDC, USDT, WBTC (500 hub pools)."""
    out = [[token, f, WETH] for f in FEES]
    for hub in HUBS:
        out += [[token, f, hub, 500, WETH] for f in FEES]
    return out


def quote(s, amounts, block='latest'):
    """Best sale path and WETH out for {token: amount}, QuoterV2 through the lens, 8 tokens per eth_call."""
    toks = list(amounts)
    for i in range(0, len(toks), 8):
        chunk = toks[i:i + 8]
        paths = [pp for t in chunk for pp in sale_paths(t)]
        per = len(paths) // len(chunk)
        heads, tails, off = '', '', 32 * len(paths)
        for pp in paths:
            e = enc_bytes(path_hex(pp))
            heads += word(off)
            tails += e
            off += len(e) // 2
        paths_enc = word(len(paths)) + heads + tails
        data = (SEL_BEST_ROUTES + aword(QUOTER) + word(0x80) + word(0x80 + len(paths_enc) // 2) + word(per)
                + paths_enc + word(len(chunk)) + ''.join(word(amounts[t]) for t in chunk))
        out = lens_call(data, block)
        o_idx, o_out = at(out, 0) // 32, at(out, 1) // 32
        for j, t in enumerate(chunk):
            got = at(out, o_out + 1 + j)
            s['rate'][t] = {'path': paths[j * per + at(out, o_idx + 1 + j)], 'r': got / amounts[t], 'out': got}


def select_assets(s, bals, block='latest', requote=True):
    """Up to 20 assets by quoted WETH proceeds; WETH and native count at face value."""
    held = {t: b for t, b in bals.items() if b > 0 and t not in (WETH, NATIVE)}
    new = {t: b for t, b in held.items() if t not in s['rate']}
    if new:
        quote(s, new, block)
    est = sorted(((b * s['rate'][t]['r'], t) for t, b in held.items()), reverse=True)[:MAX_ASSETS + 4]
    if requote:
        fresh = {t: held[t] for v, t in est if v >= MIN_ASSET_WEI and t not in new}
        if fresh:
            quote(s, fresh, block)
    vals = [(bals.get(WETH, 0), WETH), (bals.get(NATIVE, 0), NATIVE)]
    vals += [(int(held[t] * s['rate'][t]['r']), t) for _, t in est]
    vals = sorted([x for x in vals if x[0] >= MIN_ASSET_WEI], reverse=True)[:MAX_ASSETS]
    return [a for _, a in vals], sum(v for v, _ in vals)


def leg_candidates(threshold):
    """Splits of the UNI purchase (exactOutput paths, output token first). Venues copied from the incumbent:
    the WETH/UNI 0.3% pool, the USDC/UNI 0.3% pool and the LINK/UNI 0.3% pool."""
    direct, usdc, link = [UNI, 3000, WETH], [UNI, 3000, USDC, 500, WETH], [UNI, 3000, LINK, 3000, WETH]
    out = [[[direct, threshold]]]
    for u, l in ((150, 0), (150, 50), (125, 50), (150, 75), (125, 75), (175, 50)):     # per mille of the threshold
        tu, tl = threshold * u // 1000, threshold * l // 1000
        legs = [[direct, threshold - tu - tl], [usdc, tu]] + ([[link, tl]] if tl else [])
        out.append(legs)
    return out


def build_steps(s, assets, nonce, legs, executor, sim_float=0):
    """Encoded Step list: collects, UNI purchase, release, sales. legs: [[path parts, uni amount]]."""
    steps = [enc_step(to, d) for to, d in collect_calls(s)]
    steps.append(enc_step(WETH, SEL_APPROVE + aword(ROUTER) + word(FLASH_WETH)))
    for parts, amt in legs:
        steps.append(enc_step(ROUTER, SEL_EXACT_OUT + word(0x20) + word(0x80) + aword(executor) + word(amt)
                              + word(FLASH_WETH) + enc_bytes(path_hex(parts))))
    steps.append(enc_step(WETH, SEL_APPROVE + aword(ROUTER) + word(0)))
    steps.append(enc_step(UNI, SEL_APPROVE + aword(RELEASER) + word(s['threshold'])))
    steps.append(enc_step(RELEASER, SEL_RELEASE + word(nonce) + word(0x60) + aword(executor) + word(len(assets))
                          + ''.join(aword(a) for a in assets)))
    for a in assets:
        if a in (WETH, NATIVE):
            continue
        p = path_hex(s['rate'][a]['path'])
        steps.append(enc_step(a, SEL_APPROVE + aword(ROUTER) + word(0), bal_token=a, bal_offset=4 + 32))
        steps.append(enc_step(ROUTER, SEL_EXACT_IN + word(0x20) + word(0x80) + aword(executor) + word(0) + word(0)
                              + enc_bytes(p), bal_token=a, bal_offset=4 + 32 + 64))
    if sim_float:
        steps.append(enc_step(WETH, SEL_DEPOSIT, value=sim_float))   # read-only distance simulation only
    return steps


def bot_address():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a.get('address') if isinstance(a, dict) else a   # my_address() returns {"ok":..., "address":...}
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def distance(s, assets, nonce, legs, ctx, block='latest'):
    """Signed gain in wei of the plan (negative while the jar is below the threshold), by one eth_call:
    the executor is lent SIM_FLOAT native by a state override, so the run reaches the final check and
    reports its end balance in NoProfit(end, need) or returns the profit."""
    frm, to, ov = ctx
    steps = build_steps(s, assets, nonce, legs, to, sim_float=SIM_FLOAT)
    over = dict(ov or {})
    over[to] = dict(over.get(to, {}), balance=hex(SIM_FLOAT))
    params = [{'from': frm, 'to': to, 'data': enc_run(steps, 0), 'gas': hex(30_000_000)}, block, over]
    try:
        return at(rpc('eth_call', params), 0), None
    except CallReverted as e:
        d = e.data
        if d.startswith(ERR_NOPROFIT) and len(d) >= 10 + 128:
            return int(d[10:74], 16) - SIM_FLOAT, None
        return None, d[:138]


def sim_exact(s, assets, nonce, legs, ctx, min_profit, block='latest'):
    frm, to, ov = ctx
    data = enc_run(build_steps(s, assets, nonce, legs, to), min_profit)
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(30_000_000)}, block] + ([ov] if ov else [])
    return at(rpc('eth_call', params), 0), data


def eth_usd(block='latest'):
    pool = '0x' + call(FACTORY, SEL_GETPOOL + aword(WETH) + aword(USDC) + word(500), block)[-40:]
    sqrt_p = at(call(pool, SEL_SLOT0, block), 0)
    return (sqrt_p / 2**96) ** 2 * 1e12      # token0 WETH (18), token1 USDC (6)


def send_live(data, gas_limit, max_fee, prio, gross_wei, cap_wei, nonce):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=prio)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', release_nonce=nonce, reply=reply)   # final, never retried
        return
    log('send', hash=h, release_nonce=nonce, gas_limit=gas_limit, max_fee=max_fee, priority=prio,
        gross_wei=gross_wei, gas_cap_wei=cap_wei, executor=EXEC)
    receipt = None
    for _ in range(30):
        time.sleep(1)
        try:
            receipt = rpc('eth_getTransactionReceipt', [h])
        except Exception:
            receipt = None
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, release_nonce=nonce, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    wb, wtx = (b, h) if status else (None, None)
    if not status:
        try:
            logs = rpc('eth_getLogs', [{'address': RELEASER, 'fromBlock': hex(b - 2000), 'toBlock': hex(b + 50),
                                        'topics': [RELEASED_TOPIC, '0x' + word(nonce)]}])
            if logs:
                wb, wtx = int(logs[0]['blockNumber'], 16), logs[0]['transactionHash']
        except Exception:
            pass
    log('send_result', hash=h, release_nonce=nonce, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16), send_block=b, winner_block=wb, winner_tx=wtx,
        blocks_after_winner=(b - wb if wb is not None else None), gross_wei=gross_wei)


def evaluate(s, ctx):
    """One timed look: jar contents after collects, distance of the best leg split; send (live) or log (paper)."""
    nonce = at(call(RELEASER, SEL_NONCE), 0)
    bals = probe(s)
    assets, spot = select_assets(s, bals, requote=(s.get('gain') is None or s['gain'] > -3 * 10**17))
    cands = leg_candidates(s['threshold'])
    legs = cands[s.get('best_leg', 0) % len(cands)]
    gain, err = distance(s, assets, nonce, legs, ctx)
    if gain is None:
        log('simulate_revert', release_nonce=nonce, data=err, assets=assets)
        s['gain'] = None
        return
    if gain > -2 * 10**16:      # close: try the other splits too (a few extra calls only near the threshold)
        for i, c in enumerate(cands):
            if c == legs:
                continue
            g, _ = distance(s, assets, nonce, c, ctx)
            if g is not None and g > gain:
                gain, legs, s['best_leg'] = g, c, i
    s['gain'] = gain
    log('distance', release_nonce=nonce, gain_wei=gain, gain_eth=gain / 1e18, jar_spot_eth=spot / 1e18,
        assets=len(assets), leg_split=[x[1] // 10**18 for x in legs])
    if gain <= 0:
        return
    price = eth_usd()
    frm, to, ov = ctx
    probe_data = enc_run(build_steps(s, assets, nonce, legs, to), 1)
    try:
        est = int(rpc('eth_estimateGas', [{'from': frm, 'to': to, 'data': probe_data}, 'latest'] + ([ov] if ov else [])), 16)
    except CallReverted as e:
        log('simulate_revert', release_nonce=nonce, stage='estimate', data=e.data[:138])
        return
    gas_limit = est * 13 // 10
    base = int(rpc('eth_gasPrice', []), 16)
    fee_ceiling = int(GAS_CAP_USD / price * 1e18 / gas_limit)      # maxFeePerGas x gasLimit <= 0.90 USD
    prio = min(int(gain * BID_SHARE / gas_limit), max(0, fee_ceiling - base))
    max_fee = min(fee_ceiling, 2 * base + prio)
    cap_wei = max_fee * gas_limit
    gross_usd, cap_usd = gain / 1e18 * price, cap_wei / 1e18 * price
    row = dict(release_nonce=nonce, gross_wei=gain, gross_usd=gross_usd, gas_limit=gas_limit, max_fee=max_fee,
               priority=prio, gas_cap_usd=cap_usd, base_fee=base)
    if max_fee < base or gain <= cap_wei:          # send only when expected gross > this send's gas cap
        log('opportunity_skip', reason='gross_below_gas_cap' if max_fee >= base else 'base_fee_above_cap', **row)
        return
    try:
        profit, data = sim_exact(s, assets, nonce, legs, ctx, cap_wei)   # on-chain minProfit = the gas cap
    except CallReverted as e:
        log('simulate_revert', release_nonce=nonce, stage='final', data=e.data[:138])
        return
    log('opportunity', sim_profit_wei=profit, **row)
    if MODE == 'live':
        send_live(data, gas_limit, max_fee, prio, gain, cap_wei, nonce)
    else:
        log('paper_send', release_nonce=nonce, sim_profit_wei=profit, gas_cap_wei=cap_wei, executor=to)


def refresh_template(s, tx_hash=None):
    """Add the newest public release to the copied history (last HISTORY) and rebuild the candidates."""
    if not s.get('history'):
        s['history'] = json.loads((HERE / 'seed-template.json').read_text())['history']
    if tx_hash and tx_hash not in [h['tx'] for h in s['history']]:
        tpl = template_from_tx(tx_hash, adapters())
        if tpl['v3_pools'] and tpl['assets']:
            s['history'] = (s['history'] + [tpl])[-HISTORY:]
        else:
            log('template_unusable', tx=tx_hash, v3_pools=len(tpl['v3_pools']), assets=len(tpl['assets']))
    refresh_cands(s)
    pools, v4, assets = union(s['history'])
    log('template', txs=[h['tx'] for h in s['history']], v3_pools=len(pools), v4_calls=len(v4),
        candidates=len(s['tokens']), threshold=s['threshold'], v3_adapter=s['v3_adapter'])


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def save_state(s):
    try:
        STATE.parent.mkdir(exist_ok=True)
        tmp = STATE.with_suffix('.tmp')
        tmp.write_text(json.dumps(s, separators=(',', ':')))
        tmp.replace(STATE)
    except OSError:
        pass


def feed_wait(cursor, timeout):
    q = {'address': RELEASER, 'topic0': RELEASED_TOPIC, 'timeout': str(timeout)}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=timeout + 10) as r:
        return json.load(r)


def cadence(gain):
    """Seconds between looks: the jar fills at roughly 0.004 ETH/min, so look often only near the threshold."""
    if gain is None or gain < -10**17:
        return 300
    if gain < -2 * 10**16:
        return 60
    return 15


def main():
    s = load_state()
    ctx = exec_ctx()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), owner=ctx[0])
    refresh_template(s)
    last = 0
    while True:
        try:
            if time.time() - last >= cadence(s.get('gain')):
                last = time.time()
                evaluate(s, ctx)
                save_state(s)
            wait = max(5, min(55, int(cadence(s.get('gain')) - (time.time() - last))))
            result = feed_wait(s.get('feed_cursor'), wait)
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            logs = [x for x in (result.get('logs') or []) if not x.get('removed')]
            if logs:
                x = logs[-1]
                log('released_seen', tx=x.get('transactionHash'), block=x.get('blockNumber'),
                    recipient='0x' + x['topics'][2][26:], release_nonce=int(x['topics'][1], 16),
                    our_last_gain_wei=s.get('gain'))
                refresh_template(s, x.get('transactionHash'))
                s['gain'] = None
                last = 0
            elif result.get('gap'):
                last = 0     # re-read the state through the relay right away
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('feed_error', error=str(e)[:180])   # 429/503/timeout: the timed look goes on without the feed
            time.sleep(min(55, cadence(s.get('gain'))))
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(15)
        save_state(s)


if __name__ == '__main__':
    main()
