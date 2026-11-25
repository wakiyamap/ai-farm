#!/usr/bin/env python3
"""trial-dolomite-arbitrum: cheap-chain trial of Dolomite liquidations on Arbitrum One (native USDC debt).

A timer scans the Dolomite accounts that owe USDC (getAdjustedAccountValues through Multicall3, the ones nearest
to the margin threshold every 45 s). For an account under the threshold it simulates the exact executor call:
Dolomite's own LiquidatorProxyV2WithExternalLiquidity liquidates into the executor's Dolomite account and sells
the seized collateral for USDC through Augustus V5 directUniV3Swap, the surplus USDC is withdrawn to the bot
wallet, and the executor reverts unless that balance grew by minProfit. No capital: a lost attempt costs gas only.
"""
import sys
sys.path.append("/opt/farm/lib")  # live service does not put the signer library on the path
import datetime
import json
import os
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'arbitrum'

MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
MARGIN = '0x6bd780e7fdf01d77e4d475c821f1e7ae05409072'     # DolomiteMargin (emitter of the 30 LogLiquidate of the census)
PROXY = '0xcc24caa605375c011a4f7e6be7f6c2a3e377f368'      # LiquidatorProxyV2WithExternalLiquidity (verified, 20 of 30 takes)
UNIROUTER = '0xe592427a0aece92de3edee1f18e0157c05861564'  # Uniswap V3 SwapRouter, the exchange in the incumbent's calldata
USDC_MARKET = 17
WETH_MARKET = 0
_routes = json.loads((HERE / 'routes.json').read_text())
USDC = _routes['usdc']                                    # DolomiteMargin.getMarketTokenAddress(17)
ROUTES = {int(k): v for k, v in _routes['routes'].items()}  # market -> {token, paths: [hex path to USDC]}

T_WITHDRAW = '0xbc83c08f0b269b1726990c8348ffdf1ae1696244a14868d766e542a2f18cd7d4'
T_TRANSFER = '0x21281f8d59117d0399dc467dbdd321538ceffe3225e80e2bd4de6f1b3355cbc7'
T_SELL = '0xcc3330184b6d88cad87f9e9543b4d4110a6a3eaf20164ca5252d598d0acba3f1'
T_BUY = '0x2e346762bf4ae4568971c30b51fcebd2138275aafcfe12d872956e9f3e120893'
T_TRADE = '0x54d4cc60cf7d570631cc1a58942812cb0fc461713613400f56932040c3497d19'
T_LIQUIDATE = '0x1b9e65b359b871d74b1af1fc8b13b11635bfb097c4631b091eb762fda7e67dc7'
SEL_TAKE = '0xb34905b5'            # take((address,address,address,address,uint256,uint256,uint256,address,address,uint256,bytes,uint256))
SEL_ACCOUNT_PAR = '0x47d1b53c'     # getAccountPar((address,uint256),uint256)
SEL_ADJUSTED_VALUES = '0xf9416052'  # getAdjustedAccountValues((address,uint256))
SEL_ACCOUNT_BALANCES = '0x6a8194e7'  # getAccountBalances((address,uint256))
SEL_ACCOUNT_STATUS = '0xe51bfcb4'  # getAccountStatus((address,uint256)): 0 Normal, 1 Liquid, 2 Vapor
SEL_MARGIN_RATIO = '0x4f3c1542'    # getMarginRatio()
SEL_MARKET_PRICE = '0x8928378e'    # getMarketPrice(uint256)
SEL_TRY_AGGREGATE = '0xbce38bd7'

PAPER_EXEC = '0x8288bbd8c97feea5f38caec5114d58f8651790fe'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000006'  # the owner baked into that runtime
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)
_seed = json.loads((HERE / 'seed-accounts.json').read_text())
SEED = [[o.lower(), str(n)] for o, n in _seed['accounts']]   # [[owner, accountNumber as decimal string], ...]

# ---- loss guard -----------------------------------------------------------------------------
MAX_TX_USD = 0.90          # signed gas cap (maxFeePerGas x gasLimit) stays under this
MAX_FEE_WEI = 10**9        # absolute ceiling for maxFeePerGas (1 gwei); the USD cap binds first
BID_SHARE = 0.50           # the signed gas cap is at most this share of the simulated gross
MIN_BORROW_USD = 20        # skip accounts with less adjusted debt than this
SELL_HAIRCUT_BPS = 10      # sell 99.9% of the seized amount (interest and price drift until inclusion)
RELAY_CU_CAP = 90_000      # per UTC day

NEAR_COUNT = 150
SCAN_INTERVAL = 3600
POLL_INTERVAL = 45
DISCOVER_INTERVAL = 600
COOLDOWN = 60              # per account after an attempt (the next piece of an unwind is tried a minute later)
COOLDOWN_REVERT = 600      # after an account whose every simulation reverted
COOLDOWN_DUST = 6 * 3600   # after an account with no sellable collateral or a gross under MIN_GROSS_USD
MIN_GROSS_USD = 0.05
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 20}
_id = 0


class ReadBudgetExceeded(Exception):
    pass


class RpcError(Exception):
    def __init__(self, method, err):
        self.err = err
        super().__init__(f'{method}: {str(err)[:300]}')

    def reason(self):
        """Decoded Error(string) of a revert, or the raw error text."""
        d = self.err.get('data') if isinstance(self.err, dict) else None
        if isinstance(d, dict):
            d = d.get('data') or d.get('result')
        if isinstance(d, str) and d.startswith('0x08c379a0') and len(d) >= 138:
            try:
                n = int(d[74:138], 16)
                return bytes.fromhex(d[138:138 + 2 * n]).decode('latin1')
            except Exception:
                pass
        return str(self.err)[:200]


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
        raise RpcError(method, ans['error'])
    return ans['result']


def word(n):
    return format(n, '064x')


def aword(a):
    return a.lower().removeprefix('0x').zfill(64)


def at(h, i):
    return int(h[2 + i * 64:2 + (i + 1) * 64], 16)


def acct(owner, number):
    return aword(owner) + word(int(number))


def call(to, data):
    return rpc('eth_call', [{'to': to, 'data': data}, 'latest'])


def aggregate(calls):
    """One Multicall3 tryAggregate(false, [(target, data)]). Returns [(ok, returndata hex)] per call."""
    starts, acc = [], 32 * len(calls)
    for _, data in calls:
        starts.append(acc)
        size = (len(data) - 2) // 2
        acc += 96 + ((size + 31) // 32) * 32
    enc = SEL_TRY_AGGREGATE + word(0) + word(64) + word(len(calls)) + ''.join(word(x) for x in starts)
    for target, data in calls:
        size = (len(data) - 2) // 2
        enc += aword(target) + word(64) + word(size) + data[2:].ljust(((size + 31) // 32) * 64, '0')
    h = call(MULTICALL, enc)[2:]
    if len(h) < 128:
        raise RuntimeError('short Multicall answer')
    n = min(int(h[64:128], 16), len(calls))
    out = []
    for i in range(n):
        start = 128 + int(h[128 + i * 64:192 + i * 64], 16) * 2
        ok = int(h[start:start + 64], 16) != 0
        off = int(h[start + 64:start + 128], 16)
        length = int(h[start + off * 2:start + off * 2 + 64], 16)
        out.append((ok, '0x' + h[start + off * 2 + 64:start + off * 2 + 64 + length * 2]))
    return out + [(False, '0x')] * (len(calls) - len(out))


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {'accounts': list(SEED), 'near': [], 'cursor_block': None, 'margin_ratio': None,
            'last_scan': 0, 'last_poll': 0, 'last_discover': 0, 'cooldown': {}}


def save_state(s):
    now = time.time()
    s['cooldown'] = {k: v for k, v in s['cooldown'].items() if v > now}
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def bot_address():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a.get('address') if isinstance(a, dict) else a   # my_address() returns {"ok":..., "address":...}
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def calldata(owner, number, held_market, held_token, sell, path, min_profit):
    # take(TakeParams): the tuple holds a dynamic bytes, so it sits behind one offset word. Head = 12 words
    # (proxy, margin, uniRouter, liquidOwner, liquidNumber, owedMarket, heldMarket, heldToken, owedToken,
    #  sellAmount, offset of path, minProfit), then the path (length, bytes padded to 32).
    p = path.removeprefix('0x')
    size = len(p) // 2
    return (SEL_TAKE + word(32) + aword(PROXY) + aword(MARGIN) + aword(UNIROUTER) + aword(owner) + word(int(number))
            + word(USDC_MARKET) + word(held_market) + aword(held_token) + aword(USDC) + word(sell) + word(12 * 32)
            + word(min_profit) + word(size) + p.ljust(((size + 31) // 32) * 64, '0'))


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def sim(data, ctx):
    """Returns (gain, None) or (None, revert reason)."""
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(6_000_000)}, 'latest'] + ([ov] if ov else [])
    try:
        return at(rpc('eth_call', params), 0), None
    except RpcError as e:
        return None, e.reason()


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def balances_of(owner, number):
    """getAccountBalances -> {market: (token, signed wei)}."""
    h = call(MARGIN, SEL_ACCOUNT_BALANCES + acct(owner, number))
    body = h[2:]

    def arr(i):
        off = int(body[i * 64:(i + 1) * 64], 16) * 2
        n = int(body[off:off + 64], 16)
        return off + 64, n
    m_off, n = arr(0)
    t_off, _ = arr(1)
    w_off, _ = arr(3)
    if n > 64:
        raise RuntimeError(f'bad market count {n}')
    out = {}
    for i in range(n):
        market = int(body[m_off + i * 64:m_off + (i + 1) * 64], 16)
        token = '0x' + body[t_off + i * 64:t_off + (i + 1) * 64][-40:]
        sign = int(body[w_off + i * 128:w_off + i * 128 + 64], 16)
        value = int(body[w_off + i * 128 + 64:w_off + (i + 1) * 128], 16)
        out[market] = (token, value if sign else -value)
    return out


def pull_ok(why):
    """True when a simulated take got past the Augustus pull (the sell amount was not above the seized amount)."""
    return why is None or 'insufficient output' in why or 'no profit' in why


def size_sell(owner, number, market, token, path, held_wei, owed_wei, p_held, p_usdc, ctx):
    """Largest sell amount the proxy lets Augustus pull = the seized collateral. The proxy approves exactly the
    seized amount, so a larger sell reverts in the pull and a smaller one leaves the rest behind.
    Returns (amount, None) or (None, reason)."""
    def ok(amount):
        return pull_ok(sim(calldata(owner, number, market, token, amount, path, 0), ctx)[1])
    _, why = sim(calldata(owner, number, market, token, held_wei, path, 0), ctx)
    if pull_ok(why):
        return held_wei, None                       # the whole collateral balance is seized
    if any(x in why for x in ('Unliquidatable', 'not whitelisted', 'cannot be', 'Sender not operator')):
        return None, why                            # the proxy refuses this account or market: nothing to size
    est = max(1, owed_wei * p_usdc // p_held)       # seized = est x (1 + spread) when the whole USDC debt is taken
    lo, hi, n = est, min(est * 5 // 4, held_wei), 0
    if lo >= hi or not ok(lo):
        lo, hi = max(1, held_wei // 10_000), held_wei   # a dust amount fails inside the swap ('AS'), so start above it
        if not ok(lo):
            return None, 'sizing: no pullable amount; ' + why
    elif hi < held_wei and ok(hi):
        lo, hi = hi, held_wei
    while hi - lo > max(1, lo // 2000) and n < 24:
        mid = (lo + hi) // 2
        n += 1
        if ok(mid):
            lo = mid
        else:
            hi = mid
    return lo, None


def winner_block(owner, send_block, our_hash):
    """Block of the LogLiquidate that took this account owner near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': MARGIN, 'fromBlock': hex(max(0, send_block - 400)), 'toBlock': hex(head),
                                'topics': [T_LIQUIDATE, None, '0x' + aword(owner)]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None, None
    if not logs:
        return None, None, None
    first = min(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(first['blockNumber'], 16), first['transactionHash'], int(first.get('transactionIndex', '0x0'), 16)


def send_live(owner, number, market, data, gas_limit, max_fee, gross_usd, gas_cap_usd):
    import farmbot_signer
    # Arbitrum orders first come, first served: no priority fee is bid.
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=0)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', owner=owner, number=number, held_market=market, reply=reply)  # final, never retried
        return
    log('send', hash=h, owner=owner, number=number, held_market=market, gas_limit=gas_limit, max_fee=max_fee, priority=0,
        gross_usd=gross_usd, gas_cap_usd=gas_cap_usd, executor=EXEC)
    receipt = None
    for _ in range(30):
        time.sleep(1)
        try:
            receipt = rpc('eth_getTransactionReceipt', [h])
        except ReadBudgetExceeded:
            break
        except Exception:
            receipt = None
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, owner=owner, number=number, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt.get('effectiveGasPrice', hex(max_fee)), 16)
    try:
        wb, wtx, widx = winner_block(owner, b, h)
    except Exception:
        wb, wtx, widx = None, None, None
    log('send_result', hash=h, owner=owner, number=number, held_market=market, result='won' if status else 'lost',
        gas_used=used, gas_cost_wei=cost, send_block=b, winner_block=wb, winner_tx=wtx, winner_tx_index=widx,
        blocks_after_winner=(b - wb if wb is not None else None), gross_usd=gross_usd)


def attempt(s, owner, number, supply, borrow, trigger):
    now = time.time()
    key = owner + ':' + number
    if s['cooldown'].get(key, 0) > now:
        return
    s['cooldown'][key] = now + COOLDOWN
    health = round(supply / borrow, 5) if borrow else None
    bals = balances_of(owner, number)
    owed_wei = -bals.get(USDC_MARKET, (None, 0))[1]
    if owed_wei <= 0:
        return
    held = [(m, tok, wei) for m, (tok, wei) in bals.items()
            if wei > 0 and m in ROUTES and ROUTES[m]['token'].lower() == tok.lower() and ROUTES[m]['paths']]
    if not held:
        s['cooldown'][key] = now + COOLDOWN_DUST   # e.g. an account left marked Liquid with collateral this bot cannot sell
        log('opportunity_skip', owner=owner, number=number, health=health, reason='no_route_for_collateral',
            markets={m: str(v[1]) for m, v in bals.items()}, trigger=trigger)
        return
    mk = sorted({m for m, _, _ in held} | {USDC_MARKET, WETH_MARKET})
    res = aggregate([(MARGIN, SEL_MARKET_PRICE + word(m)) for m in mk])
    price = {m: int(r, 16) for m, (ok, r) in zip(mk, res) if ok and len(r) >= 66}
    eth_usd = price.get(WETH_MARKET, 0) / 1e18      # Dolomite price x wei = USD x 1e36
    if not (300 < eth_usd < 30000) or not price.get(USDC_MARKET):
        log('opportunity_skip', owner=owner, number=number, reason='no_eth_or_usdc_price', eth_usd=eth_usd)
        return
    held = sorted((x for x in held if price.get(x[0])), key=lambda x: x[2] * price[x[0]], reverse=True)[:2]
    ctx = exec_ctx()
    best, last_error = None, None
    for market, tok, wei in held:
        paths = ROUTES[market]['paths'][:2]
        seized, why = size_sell(owner, number, market, tok, paths[0], wei, owed_wei, price[market], price[USDC_MARKET], ctx)
        if seized is None:
            last_error = why
            if 'Unliquidatable' in (why or ''):
                break
            continue
        sell = seized * (10_000 - SELL_HAIRCUT_BPS) // 10_000
        for path in paths:
            gain, why = sim(calldata(owner, number, market, tok, sell, path, 0), ctx)
            if gain is None:
                last_error = why
                continue
            if best is None or gain > best[0]:
                best = (gain, market, tok, sell, path)
    if best is None:
        s['cooldown'][key] = now + COOLDOWN_REVERT
        log('simulate_revert', owner=owner, number=number, health=health, error=(last_error or '')[:200], trigger=trigger)
        return
    gain, market, tok, sell, path = best
    gross_usd = gain / 1e6   # the gain is always native USDC (6 decimals)
    if gross_usd < MIN_GROSS_USD:
        s['cooldown'][key] = now + COOLDOWN_DUST   # dust left in an account that stays marked Liquid
        log('opportunity_skip', owner=owner, number=number, held_market=market, health=health, gross_usd=gross_usd,
            reason='gross_under_min', trigger=trigger)
        return
    try:
        gas_limit = estimate(calldata(owner, number, market, tok, sell, path, 0), ctx) * 6 // 5   # from eth_estimateGas, never a constant
        base_fee = int(rpc('eth_gasPrice', []), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', owner=owner, number=number, health=health, error='estimate: ' + str(e)[:140])
        return
    # maxFeePerGas: twice the current gas price, but maxFee x gasLimit < MAX_TX_USD and <= BID_SHARE of the gross.
    fee_ceiling = int(min(MAX_TX_USD, gross_usd * BID_SHARE) / eth_usd * 1e18 / gas_limit) - 1
    max_fee = min(MAX_FEE_WEI, 2 * base_fee, fee_ceiling)
    gas_cap_usd = gas_limit * max_fee / 1e18 * eth_usd
    if max_fee * 10 < base_fee * 11 or gas_cap_usd >= MAX_TX_USD or gross_usd <= gas_cap_usd:
        log('opportunity_skip', owner=owner, number=number, held_market=market, health=health, gross_usd=gross_usd,
            gas_cap_usd=gas_cap_usd, base_fee=base_fee, max_fee=max_fee, gas_limit=gas_limit,
            reason='gross_not_above_gas_cap_or_fee_too_high', trigger=trigger)
        return
    # On-chain floor: the executor reverts unless the USDC gain covers the signed gas cap.
    min_profit = int(gas_cap_usd * 1e6) + 1
    data = calldata(owner, number, market, tok, sell, path, min_profit)
    gain, why = sim(data, ctx)  # the exact bytes that would be sent
    if gain is None:
        log('simulate_revert', owner=owner, number=number, held_market=market, health=health, error='final: ' + (why or '')[:140])
        return
    log('opportunity', owner=owner, number=number, held_market=market, held_token=tok, path=path, health=health,
        borrow_usd=borrow / 1e36, usdc_debt=owed_wei / 1e6, sell=sell, gross_usd=gross_usd, gas_cap_usd=gas_cap_usd,
        gas_limit=gas_limit, max_fee=max_fee, base_fee=base_fee, min_profit=min_profit, simulated_gain=gain,
        trigger=trigger, mode=MODE)
    if MODE == 'live':
        send_live(owner, number, market, data, gas_limit, max_fee, gross_usd, gas_cap_usd)
    else:
        log('paper_sim', owner=owner, number=number, held_market=market, result='success', gain=gain, gross_usd=gross_usd)


def margin_ratio(s):
    mr = s.get('margin_ratio')
    if not mr or mr[1] < time.time() - 3600:
        mr = [at(call(MARGIN, SEL_MARGIN_RATIO), 0), time.time()]
        s['margin_ratio'] = mr
    return mr[0]


def scan(s, accounts, label):
    """getAdjustedAccountValues -> (supply, borrow) in USD x 1e36; under water when supply < borrow x (1 + marginRatio).
    The full scan also reads the USDC par, so only accounts that owe USDC enter the near list."""
    full = label == 'full'
    mr = margin_ratio(s)
    eligible, debtors, ratios, n_marked = [], [], [], 0
    step = 100 if full else 150
    for off in range(0, len(accounts), step):
        batch = accounts[off:off + step]
        calls = []
        for o, n in batch:
            calls.append((MARGIN, SEL_ADJUSTED_VALUES + acct(o, n)))
            calls.append((MARGIN, SEL_ACCOUNT_STATUS + acct(o, n)))
            if full:
                calls.append((MARGIN, SEL_ACCOUNT_PAR + acct(o, n) + word(USDC_MARKET)))
        try:
            data = aggregate(calls)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('scan_error', label=label, offset=off, error=str(e)[:200])
            continue
        k = 3 if full else 2
        for i, (o, n) in enumerate(batch):
            ok, ret = data[i * k]
            if not ok or len(ret) < 2 + 128:
                continue
            supply, borrow = at(ret, 0), at(ret, 1)
            oks, st = data[i * k + 1]
            marked = oks and len(st) >= 66 and at(st, 0) == 1   # Account.Status.Liquid
            if full:
                okp, par = data[i * k + 2]
                if not okp or len(par) < 2 + 128 or at(par, 0) != 0 or at(par, 1) == 0:
                    continue      # owes no USDC now
            if borrow < MIN_BORROW_USD * 10**36:
                continue
            # An account already marked Liquid stays liquidatable above the threshold until its owner acts
            # (the later pieces of an unwind): it sorts first and is always tried.
            debtors.append((0.0 if marked else supply / borrow, o, n))
            ratios.append(supply / borrow)
            if marked or supply * 10**18 < borrow * (10**18 + mr):
                eligible.append((borrow, supply, o, n))
                n_marked += 1 if marked else 0
    if full:
        debtors.sort()
        s['near'] = [[o, n] for _, o, n in debtors[:NEAR_COUNT]]
    log('scan', label=label, checked=len(accounts), debtors=len(debtors), underwater=len(eligible), marked_liquid=n_marked,
        near=len(s['near']),
        min_ratio=(round(min(ratios), 5) if ratios else None), threshold=1 + mr / 1e18)
    eligible.sort(reverse=True)  # largest debt first
    for borrow, supply, o, n in eligible[:3]:
        try:
            attempt(s, o, n, supply, borrow, label)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            log('attempt_error', owner=o, number=n, error=str(e)[:200])


def neg(d, i):
    """BalanceUpdate at data word i = (deltaSign, deltaValue, parSign, parValue): True when the new par is negative."""
    return at(d, i + 2) == 0 and at(d, i + 3) > 0


def accounts_of(lg):
    t, d = lg['topics'], lg['data']
    o1 = '0x' + t[1][-40:].lower()
    out = []
    if t[0] == T_WITHDRAW and neg(d, 2):
        out.append([o1, str(at(d, 0))])
    elif t[0] == T_TRANSFER:
        if neg(d, 3):
            out.append([o1, str(at(d, 0))])
        if neg(d, 7):
            out.append(['0x' + t[2][-40:].lower(), str(at(d, 1))])
    elif t[0] in (T_SELL, T_BUY) and (neg(d, 3) or neg(d, 7)):
        out.append([o1, str(at(d, 0))])
    elif t[0] == T_TRADE:
        if neg(d, 4) or neg(d, 8):
            out.append([o1, str(at(d, 0))])
        if neg(d, 12) or neg(d, 16):
            out.append(['0x' + t[2][-40:].lower(), str(at(d, 1))])
    return out


def discover(s):
    """New borrowers: balance events of DolomiteMargin whose new par is negative (about 1,800 logs a day in total)."""
    head = int(rpc('eth_blockNumber', []), 16) - 5
    start = s['cursor_block'] + 1 if s['cursor_block'] is not None else int(_seed.get('head', head - 20000))
    start = max(start, head - 400_000)   # at most about a day of blocks per request
    if start > head:
        return
    logs = rpc('eth_getLogs', [{'address': MARGIN, 'fromBlock': hex(start), 'toBlock': hex(head),
                                'topics': [[T_WITHDRAW, T_TRANSFER, T_SELL, T_BUY, T_TRADE]]}])
    known = {(o, n) for o, n in s['accounts']}
    fresh = []
    for lg in logs:
        for o, n in accounts_of(lg):
            if (o, n) not in known:
                known.add((o, n))
                fresh.append([o, n])
    s['accounts'] += fresh
    s['near'] = (s['near'] + fresh)[:NEAR_COUNT + 100]   # new borrowers are watched until the next full scan
    s['cursor_block'] = head
    log('discover', from_block=start, to_block=head, logs=len(logs), added=len(fresh), universe=len(s['accounts']))


def main():
    s = load_state()
    known = {(o, n) for o, n in s['accounts']}
    extra = [p for p in SEED if (p[0], p[1]) not in known]
    if extra:   # a newer seed file adds to a saved universe and forces a full scan
        s['accounts'] += extra
        s['last_scan'] = 0
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), universe=len(s['accounts']),
        routes=sorted(ROUTES), proxy=PROXY)
    while True:
        now = time.time()
        try:
            if now - s['last_discover'] >= DISCOVER_INTERVAL:
                s['last_discover'] = now
                discover(s)
            if now - s['last_scan'] >= SCAN_INTERVAL:
                s['last_scan'] = now
                s['last_poll'] = now
                scan(s, s['accounts'], 'full')
            elif now - s['last_poll'] >= POLL_INTERVAL:
                s['last_poll'] = now
                scan(s, s['near'], 'near')
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            save_state(s)
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)
        time.sleep(max(1.0, POLL_INTERVAL - (time.time() - s['last_poll'])))


if __name__ == '__main__':
    main()
