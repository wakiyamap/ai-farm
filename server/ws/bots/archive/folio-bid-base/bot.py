#!/usr/bin/env python3
"""folio-bid-base: flash-funded bids on Reserve Folio (index DTF) rebalance auctions on Base.

A Folio rebalance opens Dutch auctions (15-30 min) in which anyone may buy the basket's surplus token for its
deficit token at a price that only falls. The bot polls nextAuctionId() of the watched Folios once a minute.
While an auction is open it reads getBid() for every ordered token pair every few seconds and simulates the
exact executor call (Morpho WETH flash loan -> buy the deficit token on a V3 pool -> Folio.bid -> sell the
surplus token for WETH -> repay). In live mode it sends as soon as the simulated gain clears a low line
(MIN_NET_WEI and 3x the signed gas cap): the incumbents wait for about 1 USD per lot, the bot takes the lot
earlier at a lower line. The executor reverts unless it ends with more native + WETH, so a lost bid costs gas only.
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
CHAIN = 'base'

WETH = '0x4200000000000000000000000000000000000006'
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'      # Morpho Blue (Base), fee-free flash loans
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'   # Multicall3
# V3 venues: router kind, router, factory (router.factory() is checked at start), fee tiers
DEXES = [
    {'kind': 'pcs', 'router': '0x1b81d678ffb9c0263b24a97847620c99d213eb14',
     'factory': '0x0bfbcf9fa4f9c56b0f40a671ad40e0805a091865', 'fees': (100, 500, 2500, 10000)},   # PancakeSwap V3 SwapRouter
    {'kind': 'uni', 'router': '0x2626664c2603336e57b271c5c0b26f421741e481',
     'factory': '0x33128a8fc17869897dce68ed026d694621f6fdfd', 'fees': (100, 500, 3000, 10000)},   # Uniswap V3 SwapRouter02
]
# Reserve index DTFs on Base (api.reserve.org/discover/dtf?chainId=8453, 2026-11-18), the six largest
FOLIOS = {
    '0x4da9a0f397db1397902070f93a4d6ddbc0e0e6e8': 'LCAP',
    '0x23418de10d422ad71c9d5713a2b8991a9c586443': 'BGCI',
    '0xe00cfa595841fb331105b93c19827797c925e3e4': 'VLONE',
    '0xebcda5b80f62dd4dd2a96357b42bb6facbf30267': 'ABX',
    '0xe8b46b116d3bdfa787ce9cf3f5acc78dc7ca380e': 'MVTT10F',
    '0x44551ca46fa5592bb572e20043f7c3d54c85cad7': 'CLX',
}

# selectors (cast sig; scratch/folio-bid-base/sigs.py)
SEL_RUN = '0x2472f7dc'        # run(address,address,uint256,(address,uint256,bytes,address,uint256)[],uint256)
SEL_APPROVE = '0x095ea7b3'
SEL_BID = '0xce923605'        # bid(uint256,address,address,uint256,uint256,bool,bytes)
SEL_GETBID = '0x76990dcd'     # getBid(uint256,address,address,uint256)
SEL_AUCTIONS = '0x571a26a0'   # auctions(uint256) -> (rebalanceNonce, startTime, endTime)
SEL_NEXT = '0xfc528482'       # nextAuctionId()
SEL_ASSETS = '0x01e1d114'     # totalAssets() -> (address[], uint256[])
SEL_AGG3 = '0x82ad56cb'       # aggregate3((address,bool,bytes)[])
SEL_GETPOOL = '0x1698ee82'    # getPool(address,address,uint24)
SEL_BALANCEOF = '0x70a08231'
SEL_FACTORY = '0xc45a0155'
SEL_IN = {'pcs': '0x414bf389', 'uni': '0x04e45aaf'}    # exactInputSingle (pcs: with deadline; uni: SwapRouter02)
SEL_OUT = {'pcs': '0xdb3e2198', 'uni': '0x5023b4df'}   # exactOutputSingle
IN_AMOUNT_OFFSET = {'pcs': 4 + 32 * 5, 'uni': 4 + 32 * 4}
ERR_NOPROFIT = '31708d59'
ERR_REPAY = '7472616e7366657246726f6d207265766572746564'   # Morpho 'transferFrom reverted': the plan loses, cannot repay
BID_TOPIC = '0x8eda72ced8404ff0ffda416826fcbaed9d7326fbbc62f3bfbfb3b048f8bfe481'   # AuctionBid(uint256,address,address,uint256,uint256)
ZERO = '0x' + '00' * 20
MAXU = 2**256 - 1

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR (or EXECUTOR_ADDR_BASE) is not set: refusing to run live without the gate-deployed executor')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'

FLASH_WEI = 20 * 10**18          # WETH borrowed per bid (free; only what the buy leg needs is spent)
OVERBUY_BPS = 20                 # buy 0.2% more of the deficit token than getBid asks; the rest is sold back
MIN_NET_WEI = 300_000_000_000_000    # 0.0003 ETH (about 0.54 USD): the bot's line; the sampled incumbent kept 0.0008 ETH
GAS_CAP_MULT = 3                 # and simulated gain >= 3x the signed gas cap
MAX_FEE_WEI = 100_000_000        # 0.1 gwei ceiling for maxFeePerGas
PRIORITY_WEI = 1_000_000         # 0.001 gwei tip, the level the incumbents pay; no fee bidding
MAX_GAS_LIMIT = 1_500_000        # so maxFeePerGas x gasLimit <= 0.00015 ETH (about 0.27 USD)
IDLE_POLL = 60                   # s between nextAuctionId polls when no auction is open
TICK = 6                         # s between getBid rounds while an auction is open
MAX_SIMS_PER_TICK = 2
PAIR_REFRESH_TICKS = 12          # full ordered-pair getBid sweep every 12 ticks; in between only pairs seen biddable
PAPER_COOLDOWN = 60              # paper: log the same lot at most once a minute
RELAY_CU_CAP = 200_000           # per UTC day (idle day about 37k; a rebalance day about 150k)
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 60, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_getBlockByNumber': 20}
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
        raise RuntimeError(f'{method}: {str(ans["error"])[:400]}')
    return ans['result']


# ---- ABI helpers -------------------------------------------------------------------------------------------

def word(n):
    return format(n, '064x')


def aword(a):
    return a.lower().removeprefix('0x').zfill(64)


def at(h, i):
    return int(h[2 + i * 64:2 + (i + 1) * 64], 16)


def enc_bytes(hexdata):
    raw = hexdata.removeprefix('0x')
    n = len(raw) // 2
    return word(n) + raw + '0' * ((64 - len(raw) % 64) % 64)


def call(to, data, block='latest'):
    return rpc('eth_call', [{'to': to, 'data': data}, block])


def aggregate3(calls, block='latest'):
    """calls: [(target, calldata)] -> [(ok, returndata hex without 0x)], failures allowed."""
    heads, tails = [], []
    off = 32 * len(calls)
    for target, data in calls:
        t = aword(target) + word(1) + word(96) + enc_bytes(data)
        heads.append(word(off))
        tails.append(t)
        off += len(t) // 2
    data = SEL_AGG3 + word(32) + word(len(calls)) + ''.join(heads) + ''.join(tails)
    raw = call(MULTICALL, data, block)[2:]
    base = 64                                   # start of the array (after the outer offset word)
    n = int(raw[base:base + 64], 16)
    out = []
    for i in range(n):
        o = int(raw[base + 64 + 64 * i:base + 128 + 64 * i], 16) * 2 + base + 64
        ok = int(raw[o:o + 64], 16) == 1
        blen = int(raw[o + 128:o + 192], 16)
        out.append((ok, raw[o + 192:o + 192 + blen * 2]))
    return out


# ---- plan builder (the same step list the fork proof sends: scratch/folio-bid-base/proof.py) ------------------

def swap_in(dex, token_in, token_out, fee, recipient, deadline):
    """exactInputSingle with amountIn = 0, patched on-chain to the executor's balance of token_in."""
    head = aword(token_in) + aword(token_out) + word(fee) + aword(recipient)
    if dex['kind'] == 'pcs':
        return SEL_IN['pcs'] + head + word(deadline) + word(0) + word(0) + word(0)
    return SEL_IN['uni'] + head + word(0) + word(0) + word(0)


def swap_out(dex, token_in, token_out, fee, recipient, deadline, amount_out, max_in):
    head = aword(token_in) + aword(token_out) + word(fee) + aword(recipient)
    if dex['kind'] == 'pcs':
        return SEL_OUT['pcs'] + head + word(deadline) + word(amount_out) + word(max_in) + word(0)
    return SEL_OUT['uni'] + head + word(amount_out) + word(max_in) + word(0)


def approve(spender, amount):
    return SEL_APPROVE + aword(spender) + word(amount)


def build_steps(exe, folio, auction, sell, buy, sell_amt, max_buy, leg_buy, leg_sell, deadline, flash=FLASH_WEI):
    """leg_buy / leg_sell: (dex, fee) of the WETH pool of the buy / sell token, None when that token is WETH."""
    st = []   # (target, calldata, balToken, balOffset)
    if leg_buy:
        dex, fee = leg_buy
        st.append((WETH, approve(dex['router'], flash), ZERO, 0))
        st.append((dex['router'], swap_out(dex, WETH, buy, fee, exe, deadline, max_buy, flash), ZERO, 0))
        st.append((WETH, approve(dex['router'], 0), ZERO, 0))
    st.append((buy, approve(folio, max_buy), ZERO, 0))
    bid = SEL_BID + word(auction) + aword(sell) + aword(buy) + word(sell_amt) + word(max_buy) + word(0) + word(224) + word(0)
    st.append((folio, bid, ZERO, 0))
    st.append((buy, approve(folio, 0), ZERO, 0))
    if leg_sell:
        dex, fee = leg_sell
        st.append((sell, approve(dex['router'], 0), sell, 36))
        st.append((dex['router'], swap_in(dex, sell, WETH, fee, exe, deadline), sell, IN_AMOUNT_OFFSET[dex['kind']]))
    if leg_buy:
        dex, fee = leg_buy
        st.append((buy, approve(dex['router'], 0), buy, 36))
        st.append((dex['router'], swap_in(dex, buy, WETH, fee, exe, deadline), buy, IN_AMOUNT_OFFSET[dex['kind']]))
    return st


def run_calldata(steps, min_profit, flash=FLASH_WEI):
    tuples = []
    for target, data, bal_token, bal_off in steps:
        tuples.append(aword(target) + word(0) + word(160) + aword(bal_token) + word(bal_off) + enc_bytes(data))
    heads, off = [], 32 * len(tuples)
    for t in tuples:
        heads.append(word(off))
        off += len(t) // 2
    arr = word(len(tuples)) + ''.join(heads) + ''.join(tuples)
    return SEL_RUN + aword(MORPHO) + aword(WETH) + word(flash) + word(160) + word(min_profit) + arr


# ---- chain reads -------------------------------------------------------------------------------------------

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


def sim(data, ctx, block='latest'):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(3_000_000)}, block] + ([ov] if ov else [])
    return at(rpc('eth_call', params), 0)


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def check_dexes():
    ok = []
    for d in DEXES:
        try:
            f = '0x' + call(d['router'], SEL_FACTORY)[-40:]
        except Exception as e:
            log('dex_check_error', router=d['router'], error=str(e)[:150])
            continue
        if f.lower() == d['factory']:
            ok.append(d)
        else:
            log('dex_dropped', router=d['router'], factory_read=f)
    return ok


def next_ids(block='latest'):
    folios = list(FOLIOS)
    res = aggregate3([(f, SEL_NEXT) for f in folios], block)
    return {f: (int(r, 16) if ok and r else None) for f, (ok, r) in zip(folios, res)}


def auction_info(folio, auction, block='latest'):
    res = aggregate3([(folio, SEL_AUCTIONS + word(auction)), (folio, SEL_ASSETS)], block)
    if not res[0][0] or not res[1][0]:
        return None
    a, t = res[0][1], res[1][1]
    start, end = int(a[64:128], 16), int(a[128:192], 16)
    n = int(t[128:192], 16)
    tokens = ['0x' + t[192 + 64 * i + 24:192 + 64 * (i + 1)] for i in range(n)]
    return {'folio': folio, 'id': auction, 'start': start, 'end': end, 'tokens': tokens}


def find_legs(tokens, dexes, block='latest'):
    """For every token: the WETH pool (dex, fee) holding the most WETH. One Multicall for pools, one for balances."""
    q = [(tok, d, fee) for tok in tokens if tok != WETH for d in dexes for fee in d['fees']]
    if not q:
        return {}
    res = aggregate3([(d['factory'], SEL_GETPOOL + aword(tok) + aword(WETH) + word(fee)) for tok, d, fee in q], block)
    pools = [(tok, d, fee, '0x' + r[-40:]) for (tok, d, fee), (ok, r) in zip(q, res) if ok and r and int(r, 16)]
    if not pools:
        return {}
    bals = aggregate3([(WETH, SEL_BALANCEOF + aword(p)) for _, _, _, p in pools], block)
    best = {}
    for (tok, d, fee, pool), (ok, r) in zip(pools, bals):
        w = int(r, 16) if ok and r else 0
        if w > best.get(tok, (0,))[0]:
            best[tok] = (w, d, fee, pool)
    return {tok: {'dex': v[1], 'fee': v[2], 'pool': v[3], 'weth': v[0]} for tok, v in best.items()}


def get_bids(folio, auction, pairs, block='latest'):
    res = aggregate3([(folio, SEL_GETBID + word(auction) + aword(s) + aword(b) + word(MAXU)) for s, b in pairs], block)
    out = []
    for (s, b), (ok, r) in zip(pairs, res):
        if ok and len(r) >= 192 and int(r[0:64], 16) > 0 and int(r[64:128], 16) > 0:
            out.append({'sell': s, 'buy': b, 'sell_amt': int(r[0:64], 16), 'bid_amt': int(r[64:128], 16)})
    return out


_fee_cache = {'at': 0.0, 'val': None}


def fees():
    """(maxFeePerGas, head timestamp, head number); one read per tick (4 s cache)."""
    if time.time() - _fee_cache['at'] < 4 and _fee_cache['val']:
        return _fee_cache['val']
    blk = rpc('eth_getBlockByNumber', ['latest', False])
    base = int(blk.get('baseFeePerGas', '0x0'), 16)
    _fee_cache['val'] = (min(MAX_FEE_WEI, 2 * base + PRIORITY_WEI), int(blk['timestamp'], 16), int(blk['number'], 16))
    _fee_cache['at'] = time.time()
    return _fee_cache['val']


def plan_for(lot, auc, legs, exe, deadline, share=1.0, min_profit=1):
    sell, buy = lot['sell'], lot['buy']
    for tok in (sell, buy):
        if tok != WETH and tok not in legs:
            return None
    sell_amt = lot['sell_amt'] if share == 1.0 else int(lot['sell_amt'] * share)
    bid_amt = lot['bid_amt'] if share == 1.0 else int(lot['bid_amt'] * share) + 1
    max_buy = bid_amt * (10_000 + OVERBUY_BPS) // 10_000 + 1
    leg_buy = (legs[buy]['dex'], legs[buy]['fee']) if buy != WETH else None
    leg_sell = (legs[sell]['dex'], legs[sell]['fee']) if sell != WETH else None
    steps = build_steps(exe, auc['folio'], auc['id'], sell, buy, sell_amt, max_buy, leg_buy, leg_sell, deadline)
    return {'sell_amt': sell_amt, 'max_buy': max_buy, 'steps': steps, 'data': run_calldata(steps, min_profit)}


# ---- acting ------------------------------------------------------------------------------------------------

def winner_after(folio, auction, sell, buy, from_block, our_hash):
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': folio, 'fromBlock': hex(from_block), 'toBlock': hex(head),
                                'topics': [BID_TOPIC, '0x' + word(auction), '0x' + aword(sell), '0x' + aword(buy)]}])
    others = [x for x in logs if x['transactionHash'].lower() != (our_hash or '').lower()]
    if not others:
        return None, None
    first = min(others, key=lambda x: int(x['blockNumber'], 16))
    return int(first['blockNumber'], 16), first['transactionHash']


def send_live(auc, lot, plan, gas_limit, max_fee, sim_profit, sim_block):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, plan['data'], 0, gas_limit, max_fee, max_priority_fee_per_gas=PRIORITY_WEI)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', folio=auc['folio'], auction=auc['id'], reply=reply)   # final, never retried
        return
    log('send', hash=h, folio=auc['folio'], auction=auc['id'], sell=lot['sell'], buy=lot['buy'], sell_amt=plan['sell_amt'],
        gas_limit=gas_limit, max_fee=max_fee, priority=PRIORITY_WEI, sim_profit_wei=sim_profit, sim_block=sim_block, executor=EXEC)
    receipt = None
    for _ in range(20):
        time.sleep(1)
        try:
            receipt = rpc('eth_getTransactionReceipt', [h])
        except Exception:
            receipt = None
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee', '0x0'), 16)
    try:
        wb, wtx = winner_after(auc['folio'], auc['id'], lot['sell'], lot['buy'], sim_block, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, folio=auc['folio'], auction=auc['id'], sell=lot['sell'], buy=lot['buy'],
        result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost, send_block=b,
        winner_block=wb, winner_tx=wtx, sim_profit_wei=sim_profit)


def try_lot(auc, lot, legs, ctx, cool):
    """Simulate one lot (full size, then a quarter); log it; in live mode send when the gain clears the line."""
    key = f"{auc['folio']}:{auc['id']}:{lot['sell']}:{lot['buy']}"
    now = time.time()
    block = 'latest'
    if cool.get(key, 0) > now:
        return 0
    frm, exe, _ = ctx
    max_fee, ts, head = fees()
    deadline = ts + 600
    sims = 0
    for share in (1.0, 0.25):
        plan = plan_for(lot, auc, legs, exe, deadline, share)
        if plan is None:
            log('no_route', folio=auc['folio'], auction=auc['id'], sell=lot['sell'], buy=lot['buy'])
            cool[key] = now + 600
            return sims
        sims += 1
        try:
            profit = sim(plan['data'], ctx, block)
        except ReadBudgetExceeded:
            raise
        except Exception as e:
            msg = str(e)
            if ERR_NOPROFIT in msg or ERR_REPAY in msg:
                continue          # not yet profitable at this size: the normal state early in an auction
            if cool.get('rv:' + key, 0) <= now:      # at most one simulate_revert row per lot per minute
                cool['rv:' + key] = now + 60
                log('simulate_revert', folio=auc['folio'], auction=auc['id'], sell=lot['sell'], buy=lot['buy'],
                    share=share, error=msg[-220:])
            continue
        gas_cap = MAX_GAS_LIMIT * max_fee
        line = max(MIN_NET_WEI, GAS_CAP_MULT * gas_cap)
        row = dict(folio=auc['folio'], symbol=FOLIOS.get(auc['folio']), auction=auc['id'], sell=lot['sell'], buy=lot['buy'],
                   sell_amt=plan['sell_amt'], max_buy=plan['max_buy'], share=share, sim_profit_wei=profit, line_wei=line,
                   block=head, seconds_into_auction=ts - auc['start'], seconds_left=auc['end'] - ts)
        if profit < line:
            if cool.get('bl:' + key, 0) <= now:      # at most one below_line row per lot every 30 s
                cool['bl:' + key] = now + 30
                log('below_line', **row)
            return sims
        log('opportunity', **row)
        if MODE != 'live':
            log('paper_sim', would_send=True, **row)
            cool[key] = now + PAPER_COOLDOWN
            return sims
        gas = estimate(plan['data'], ctx)
        gas_limit = min(MAX_GAS_LIMIT, gas * 13 // 10)
        if gas_limit < gas:
            log('skip', reason='gas_over_limit', gas=gas, **row)
            return sims
        cap = gas_limit * max_fee
        if profit <= cap:                        # expected gross must exceed this send's gas cap
            log('skip', reason='gross_not_above_gas_cap', gas_cap_wei=cap, **row)
            return sims
        final = plan_for(lot, auc, legs, exe, deadline, share, min_profit=cap)   # on-chain floor: at least the gas cap
        send_live(auc, lot, final, gas_limit, max_fee, profit, head)
        cool[key] = now + 10
        return sims
    return sims


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {'next': {}, 'open': []}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def discover(s):
    """Poll nextAuctionId of every Folio; register auctions opened since the last poll."""
    ids = next_ids()
    for folio, nid in ids.items():
        if nid is None:
            continue
        prev = s['next'].get(folio)
        s['next'][folio] = nid
        first = nid - 1 if prev is None else prev
        for auction in range(max(first, nid - 3), nid):
            info = auction_info(folio, auction)
            if info and info['end'] >= time.time() - 5:
                if not any(o['folio'] == folio and o['id'] == auction for o in s['open']):
                    s['open'].append(info)
                    log('auction_open', folio=folio, symbol=FOLIOS[folio], auction=auction, start=info['start'],
                        end=info['end'], tokens=info['tokens'], seconds_since_start=round(time.time() - info['start']))


def main():
    s = load_state()
    dexes = check_dexes()
    if not dexes:
        raise SystemExit('no V3 router passed the factory() check')
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), folios=list(FOLIOS.values()),
        dexes=[d['router'] for d in dexes], next=s['next'])
    ctx = None
    legs_cache, pairs_cache, cool = {}, {}, {}
    last_poll, tick = 0.0, 0
    while True:
        try:
            now = time.time()
            s['open'] = [o for o in s['open'] if o['end'] >= now - 5]
            if now - last_poll >= (IDLE_POLL if not s['open'] else 30):
                last_poll = now
                discover(s)
                save_state(s)
            if not s['open']:
                legs_cache.clear()
                pairs_cache.clear()
                time.sleep(IDLE_POLL)
                continue
            if ctx is None:
                ctx = exec_ctx()
            tick += 1
            budget = MAX_SIMS_PER_TICK
            for auc in s['open']:
                key = f"{auc['folio']}:{auc['id']}"
                if key not in legs_cache:
                    legs_cache[key] = find_legs(auc['tokens'], dexes)
                    log('routes', folio=auc['folio'], auction=auc['id'],
                        legs={t: {'router': v['dex']['router'], 'fee': v['fee'], 'pool': v['pool'], 'weth': v['weth']}
                              for t, v in legs_cache[key].items()})
                if key not in pairs_cache or tick % PAIR_REFRESH_TICKS == 0:
                    pairs = [(a, b) for a in auc['tokens'] for b in auc['tokens'] if a != b]
                else:
                    pairs = pairs_cache[key]
                lots = get_bids(auc['folio'], auc['id'], pairs)
                seen = set(pairs_cache.get(key, [])) | {(l['sell'], l['buy']) for l in lots}
                pairs_cache[key] = sorted(seen)
                # rotate so that every biddable pair gets simulated within a few ticks
                lots = lots[tick % len(lots):] + lots[:tick % len(lots)] if lots else []
                for lot in lots:
                    if budget <= 0:
                        break
                    budget -= try_lot(auc, lot, legs_cache[key], ctx, cool)
            time.sleep(TICK)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)


if __name__ == '__main__':
    main()
