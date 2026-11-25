#!/usr/bin/env python3
"""trial-gmx-buyback-slow-arbitrum: take GMX v2 FeeHandler buyback batches of the slow fee tokens on Arbitrum.

GMX's FeeHandler sells the protocol's accrued fees to anyone: pay one batch (1.5 WETH) and receive the fee token at the
oracle price plus 0.4-0.6 pct, capped by the amount available. USDC and WBTC pots are taken inside the block they cross
(lead 294). The pots of the other fee tokens (USDG, LINK, ARB, SOL, ...) sit: the USDG pot held 9-12 batches for more
than 7 days in 2026-11. The bot reads every configured pot on a timer. When one is worth more than a batch plus costs it
looks for signed price reports (Chainlink Data Streams) for that token and WETH in the calldata of GMX keeper
transactions that are already confirmed, builds the executor call (flash 1.5 WETH, claimFees, buyback, sell the fee
token along its pool path, repay), simulates it and, if the simulated gain exceeds the signed gas cap, sends it
(BOT_MODE=live) or logs a paper simulation (BOT_MODE=paper). The executor reverts unless its WETH balance grew by
minProfit, so a lost attempt costs gas only. Confirmed chain data only: no pending transactions.
"""
import datetime
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.append('/opt/farm/lib')   # farmbot_signer lives here; the live service does not add it

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'arbitrum'

# Addresses: gmx-io/gmx-synthetics deployments/arbitrum/*.json; the provider and the pools are in README.md.
FEE_HANDLER = '0x7eb417637a3e6d1c19e6d69158c47610b7a5d9b3'
DATA_STORE = '0xfd70de6b91282d8017aa4e741e9ae325cab992d8'
EVENT_EMITTER = '0xc8ee91a54287db53897056e12d9819156d3822fb'
STREAM_PROVIDER = '0xf4122df7be4ccd46d7397daf2387b3a14e53d967'   # Data Streams provider of the FeeHandler's oracle
VAULT = '0xba12222222228d8ba445958a75a0704d566bf2c8'              # Balancer V2 vault, flash fee 0
WNT = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'                # WETH
PRICE_POOL = '0xc6962004f452be9203591991d15f6b388e09e8d0'         # Uniswap V3 WETH/USDC 0.05 pct (token0 = WETH)
CFG = json.loads((HERE / 'config.json').read_text())             # tokens: markets, sell path, impact key; cast consts
C = CFG['consts']
TOKENS = {t.lower(): r for t, r in CFG['tokens'].items()}
SEL_TAKE, SEL_OUT, SEL_SLOT0, SEL_TOKEN0, SEL_TOKEN1, SEL_GETUINT = (
    C[k] for k in ('SEL_TAKE', 'SEL_OUT', 'SEL_SLOT0', 'SEL_TOKEN0', 'SEL_TOKEN1', 'SEL_GETUINT'))
TOPIC_EVENTLOG = '0x7e3bde2ba7aca4a8499608ca57f3b0c1c1c93ace63ffd3741a9fab204146fc9a'   # EventLog1, read from a receipt
TOPIC_ORACLE, TOPIC_BUYBACK = C['TOPIC_ORACLE'], C['TOPIC_BUYBACK']

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # paper code override only (runtime of the fork deployment)
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

IDLE_POLL = 900          # s between rounds of pot reads (the slow pots sit for days)
NEAR_POLL = 180          # s while some pot is within 10 pct of paying (only the near pots are re-read)
ARMED_POLL = 8           # s between report searches while a pot pays
ARMED_WINDOW = 900       # s of report searching per token, then that token rests for COOLDOWN
COOLDOWN = 7200
PRICE_TTL = 3600         # s a pool price is reused while its pot is far from paying
NEAR_RATIO = 0.90
COST_ALLOW = 0.0015      # pool fees and impact allowed for in the estimate; the simulation decides
MIN_EST_GAIN_WNT = 0.0006  # arm when the estimated gain is above this (about 1 USD, above any gas cap the bot signs)
MAX_REPORT_AGE = 20      # s; the FeeHandler allows BUYBACK_MAX_PRICE_AGE (30 s) at inclusion
REPORT_LOOKBACK = 120    # blocks searched for confirmed keeper txs (about 30 s)
SIM_GAS = 16_000_000
GAS_LIMIT_MAX = 12_000_000
GAS_MARGIN = 1.25
TIP_WEI = 1_000_000                  # 0.001 gwei, passed explicitly (the signer turns 0 into maxFee / 10)
MAX_FEE_CEIL = 100_000_000           # refuse to sign above 0.1 gwei per gas
MAX_CAP_USD = 0.90                   # refuse a send whose gasLimit x maxFeePerGas is worth more (manifest: 1 USD)
RELAY_CU_CAP = 90_000
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_blockNumber': 10, 'eth_getBlockByNumber': 16, 'eth_estimateGas': 87,
           'eth_getTransactionByHash': 17, 'eth_getTransactionReceipt': 15}

LOG = HERE / 'logs' / 'bot.jsonl'
CU_FILE = HERE / 'state' / 'cu.json'
_id = 0
_parsed = {}
_token0 = {}
_price = {}      # token -> (ts, WETH wei per raw token unit)
_rest = {}       # token -> time until which it is not armed again
_armed_since = {}
_looked = {}     # token -> (time of the last pot read, state): idle pots are read once per IDLE_POLL


class ReadBudgetExceeded(RuntimeError):
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


def enc_addrs(xs):
    return word(len(xs)) + ''.join(aword(x) for x in xs)


def enc_bytes_array(items):
    """abi encoding of bytes[] (items are hex strings without 0x)"""
    head, tail, off = '', '', 32 * len(items)
    for it in items:
        n = len(it) // 2
        body = word(n) + it + '0' * ((64 - len(it) % 64) % 64)
        head += word(off)
        tail += body
        off += len(body) // 2
    return word(len(items)) + head + tail


def enc_prices(tokens, providers, datas):
    """abi encoding of the dynamic tuple (address[],address[],bytes[])"""
    a, b, c = enc_addrs(tokens), enc_addrs(providers), enc_bytes_array(datas)
    return word(96) + word(96 + len(a) // 2) + word(96 + (len(a) + len(b)) // 2) + a + b + c


def take_calldata(token, batch, tokens, providers, datas, min_profit, min_out=1):
    """take(Plan,uint256); Plan = (vault, feeHandler, weth, batch, feeToken, markets[], minOut, prices, swapPools[]).
    Checked byte for byte against cast calldata (selftest.py)."""
    t = TOKENS[token]
    markets, prices, pools = enc_addrs(t['markets']), enc_prices(tokens, providers, datas), enc_addrs(t['path'])
    o_m = 9 * 32
    o_p = o_m + len(markets) // 2
    o_s = o_p + len(prices) // 2
    plan = (aword(VAULT) + aword(FEE_HANDLER) + aword(WNT) + word(batch) + aword(token) + word(o_m) + word(min_out)
            + word(o_p) + word(o_s) + markets + prices + pools)
    return SEL_TAKE + word(64) + word(min_profit) + plan


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


def sim(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(SIM_GAS)}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_call', params)[2:66], 16)


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


def get_uint(key):
    return int(rpc('eth_call', [{'to': DATA_STORE, 'data': SEL_GETUINT + key[2:]}, 'latest']), 16)


def pot(token):
    """available amount + the WETH-buyer share of every listed market's claimable fees, uncapped (prices 1 and 1e30)."""
    data = (SEL_OUT + word(6 * 32) + aword(token) + aword(WNT) + word(2) + word(1) + word(10**30)
            + enc_addrs(TOKENS[token]['markets']))
    return int(rpc('eth_call', [{'to': FEE_HANDLER, 'data': data}, 'latest']), 16)


def sqrt_price(pool):
    return int(rpc('eth_call', [{'to': pool, 'data': SEL_SLOT0}, 'latest'])[2:66], 16)


def eth_usd():
    """USDC per WETH from slot0 of the WETH/USDC pool (token0 = WETH 18 dec, token1 = USDC 6 dec)."""
    s = sqrt_price(PRICE_POOL)
    return s * s * 10**12 / 2**192


def pool_tokens(pool):
    """(token0, token1) of a pool, read once"""
    if pool not in _token0:
        _token0[pool] = ('0x' + rpc('eth_call', [{'to': pool, 'data': SEL_TOKEN0}, 'latest'])[26:66],
                         '0x' + rpc('eth_call', [{'to': pool, 'data': SEL_TOKEN1}, 'latest'])[26:66])
    return _token0[pool]


def path_price(token):
    """WETH wei per raw unit of the token along its sell path, from each pool's slot0 (no fees)."""
    cur, px = token, 1.0
    for pool in TOKENS[token]['path']:
        t0, t1 = pool_tokens(pool)
        s = sqrt_price(pool)
        p10 = s * s / 2**192                      # raw token1 per raw token0
        if t0 == cur:
            px, cur = px * p10, t1
        else:
            px, cur = px / p10, t0
    if cur != WNT:
        raise RuntimeError(f'sell path of {token} does not end in WETH')
    return px


SEL_MULTICALL = '0xac9650d8'   # multicall(bytes[]), cast sig; keepers batch several executions in one tx


def parse_prices(inp):
    """Reports of one keeper tx: {token: (provider, data_hex)}. A multicall(bytes[]) is unwrapped and every inner call
    parsed; per token the report with the newest observation timestamp is kept."""
    if inp[:10] != SEL_MULTICALL:
        return parse_call(inp)
    out = {}
    try:
        b = bytes.fromhex(inp[10:])
        u = lambda o: int.from_bytes(b[o:o + 32], 'big')
        base = u(0)
        n = u(base)
        if not 0 < n <= 32:
            return {}
        for i in range(n):
            o = base + 32 + u(base + 32 + 32 * i)
            ln = u(o)
            if o + 32 + ln > len(b):
                return out
            for tok, (prov, data) in parse_call('0x' + b[o + 32:o + 32 + ln].hex()).items():
                if len(data) >= 600 and (tok not in out or report_ts(data) > report_ts(out[tok][1])):
                    out[tok] = (prov, data)
    except Exception:
        pass
    return out


def parse_call(inp):
    """Keeper calls carry (address[] tokens, address[] providers, bytes[] data) as one of their first arguments
    (executeOrder: fn(bytes32 key, prices); other handlers put it elsewhere). Returns {token: (provider, data_hex)}
    for the first head word that points at such a tuple, or {}."""
    try:
        b = bytes.fromhex(inp[10:])
    except Exception:
        return {}
    u = lambda o: int.from_bytes(b[o:o + 32], 'big')
    for k in range(8):
        try:
            t = u(32 * k)
            if t % 32 or t < 64 or t + 96 > len(b):
                continue
            o_tok, o_prov, o_dat = t + u(t), t + u(t + 32), t + u(t + 64)
            if max(o_tok, o_prov, o_dat) + 32 > len(b):
                continue
            n = u(o_tok)
            if not 0 < n <= 20 or u(o_prov) != n or u(o_dat) != n:
                continue
            out = {}
            for i in range(n):
                if u(o_tok + 32 + 32 * i) >> 160 or u(o_prov + 32 + 32 * i) >> 160:
                    out = {}
                    break
                tok = '0x' + b[o_tok + 32 + 32 * i + 12:o_tok + 64 + 32 * i].hex()
                prov = '0x' + b[o_prov + 32 + 32 * i + 12:o_prov + 64 + 32 * i].hex()
                o = o_dat + 32 + u(o_dat + 32 + 32 * i)
                ln = u(o)
                if o + 32 + ln > len(b):
                    out = {}
                    break
                out[tok] = (prov, b[o + 32:o + 32 + ln].hex())
            if out:
                return out
        except Exception:
            continue
    return {}


def report_ts(data_hex):
    """observationsTimestamp of a Data Streams report: abi (bytes32[3] context, bytes blob, ...); blob word 2."""
    raw = bytes.fromhex(data_hex)
    off = int.from_bytes(raw[96:128], 'big')
    if off + 128 > len(raw):
        return 0
    return int.from_bytes(raw[off + 32 + 64:off + 32 + 96], 'big')


def fresh_reports(head, token):
    """Newest confirmed reports for the fee token and WETH from GMX keeper txs in the last REPORT_LOOKBACK blocks.
    Only keeper txs that priced the fee token are fetched (WETH is in most of them, or in the newest WETH tx)."""
    want = (token, WNT)
    logs = rpc('eth_getLogs', [{'address': EVENT_EMITTER, 'fromBlock': hex(head - REPORT_LOOKBACK), 'toBlock': hex(head),
                                'topics': [None, TOPIC_ORACLE, ['0x' + aword(token), '0x' + aword(WNT)]]}])
    blk, has = {}, {}
    for l in logs:
        h = l['transactionHash']
        blk[h] = int(l['blockNumber'], 16)
        has.setdefault(h, set()).add('0x' + l['topics'][2][26:])
    with_token = sorted((h for h in has if token in has[h]), key=lambda h: -blk[h])[:4]
    with_wnt = sorted((h for h in has if WNT in has[h]), key=lambda h: -blk[h])[:16]
    best = {}
    for h in with_token + [h for h in with_wnt if h not in with_token]:
        if token in best and WNT in best and blk[h] < min(blk[best[token][3]], blk[best[WNT][3]]):
            break                                 # both found in newer txs: older ones are not fetched
        if h not in _parsed:                      # each keeper tx is fetched once
            if len(_parsed) > 200:
                _parsed.clear()
            _parsed[h] = parse_prices(rpc('eth_getTransactionByHash', [h]).get('input', '0x'))
        for tok, (prov, data) in _parsed[h].items():
            # Keepers pass the same Chainlink report bytes under their own handler's provider; the FeeHandler's oracle
            # wants STREAM_PROVIDER and accepts the bytes (wiki mechanisms/gmx-v2-fee-buyback.md).
            if tok in want and len(data) >= 600:
                ts = report_ts(data)
                if ts > best.get(tok, (0,))[0] and ts <= time.time() + 5:
                    best[tok] = (ts, STREAM_PROVIDER, data, h)
    return best


def winner(send_block, our_hash):
    """Block and tx of the newest BuybackFees event near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': EVENT_EMITTER, 'fromBlock': hex(max(0, send_block - 4000)), 'toBlock': hex(head),
                                'topics': [TOPIC_EVENTLOG, TOPIC_BUYBACK]}])
    if not logs:
        return None, None
    ours = [l for l in logs if l['transactionHash'].lower() == our_hash.lower()]
    last = ours[0] if ours else max(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(last['blockNumber'], 16), last['transactionHash']


def send_live(token, data, gas_limit, max_fee, gross, min_profit, cap_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=TIP_WEI)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply)   # final, never retried
        return
    log('send', token=TOKENS[token]['sym'], hash=h, gas_limit=gas_limit, max_fee=max_fee, priority=TIP_WEI, gross_wei=gross,
        min_profit_wei=min_profit, gas_cap_usd=cap_usd, executor=EXEC)
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
        log('send_result', hash=h, result='unknown', gas_used=None, winner_block=None)
        return
    b, status, used = int(receipt['blockNumber'], 16), int(receipt['status'], 16), int(receipt['gasUsed'], 16)
    try:
        wb, wtx = winner(b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', token=TOKENS[token]['sym'], hash=h, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16), send_block=b, winner_block=wb, winner_tx=wtx,
        blocks_after_winner=(b - wb if wb is not None else None), gross_wei=gross)


def read_params():
    p = {'batch': get_uint(C['KEY_BATCH_WNT']), 'max_age': get_uint(C['KEY_MAX_AGE']),
         'impact_wnt': get_uint(C['KEY_IMPACT_WNT']) / 1e30,
         'impact': {t: get_uint(r['key_impact']) / 1e30 for t, r in TOKENS.items()}}
    if not 10**17 <= p['batch'] <= 100 * 10**18 or p['impact_wnt'] > 0.05 or max(p['impact'].values()) > 0.05:
        raise RuntimeError(f'implausible buyback parameters {p}')
    return p


def look(p, token):
    """One pot read for one token. Returns (state, estimated gain in WETH)."""
    now = time.time()
    amount = pot(token)
    ts, px = _price.get(token, (0, 0.0))
    if now - ts > PRICE_TTL or (px and amount * px >= NEAR_RATIO * p['batch']):
        px = path_price(token)
        _price[token] = (now, px)
    batch = p['batch']
    cap = batch / px * (1 + p['impact_wnt'] + p['impact'][token])   # raw token units the buyback pays at most
    est = (min(amount, cap) * px * (1 - COST_ALLOW) - batch) / 1e18
    ratio = amount * px / batch
    state = 'armed' if est >= MIN_EST_GAIN_WNT else ('near' if ratio >= NEAR_RATIO else 'idle')
    log('check', token=TOKENS[token]['sym'], pot=amount, ratio=round(ratio, 4), est_gain_wnt=round(est, 6), state=state)
    return state, est


def attempt(p, token, ctx):
    """The pot pays by the estimate: find fresh confirmed reports, simulate, send. Returns 'done' (a send or a paper
    simulation ran), 'unprofitable' (fresh reports, but the route does not pay: the token rests) or 'wait' (no usable
    report yet)."""
    sym = TOKENS[token]['sym']
    head = int(rpc('eth_blockNumber', []), 16)
    best = fresh_reports(head, token)
    now = time.time()
    if WNT not in best or token not in best:
        log('no_reports', token=sym, head=head, have=sorted(best))
        return 'wait'
    age = now - min(best[WNT][0], best[token][0])
    if age > MAX_REPORT_AGE or age > p['max_age'] - 5:
        log('reports_stale', token=sym, head=head, age_s=round(age, 1), wnt_tx=best[WNT][3], token_tx=best[token][3])
        return 'wait'
    toks, provs, datas = [token, WNT], [best[token][1], best[WNT][1]], [best[token][2], best[WNT][2]]
    probe = take_calldata(token, p['batch'], toks, provs, datas, 1)
    try:
        gross = sim(probe, ctx)
    except ReadBudgetExceeded:
        raise
    except RuntimeError as ex:
        log('simulate_revert', token=sym, head=head, age_s=round(age, 1), err=str(ex)[:200])
        # NoProfit with fresh reports = the pool path does not return the batch; an oracle error = retry with new reports
        return 'unprofitable' if C['SEL_NOPROFIT'][2:] in str(ex) else 'wait'
    base = int(rpc('eth_getBlockByNumber', ['latest', False]).get('baseFeePerGas', '0x0'), 16)
    max_fee = int(base * 1.5) + TIP_WEI
    try:
        gas_limit = int(estimate(probe, ctx) * GAS_MARGIN)   # arbitrum: the estimate includes the L1 data component
    except ReadBudgetExceeded:
        raise
    except RuntimeError as ex:
        log('estimate_revert', token=sym, head=head, err=str(ex)[:200])
        return 'wait'
    cap_wei = gas_limit * max_fee
    cap_usd = cap_wei / 1e18 * eth_usd()
    row = dict(token=sym, head=head, report_age_s=round(age, 1), report_tx_wnt=best[WNT][3], report_tx_token=best[token][3],
               gross_wei=gross, gas_limit=gas_limit, max_fee=max_fee, cap_wei=cap_wei, gas_cap_usd=round(cap_usd, 4))
    if gas_limit > GAS_LIMIT_MAX or max_fee > MAX_FEE_CEIL or cap_usd > MAX_CAP_USD:
        log('skip_gas_cap', **row)
        return 'wait'
    if gross <= cap_wei:                      # trial rule: send only when the expected gross exceeds the send's gas cap
        log('skip_gross_below_cap', **row)
        return 'unprofitable'
    min_profit = cap_wei + 1
    data = take_calldata(token, p['batch'], toks, provs, datas, min_profit)
    log('opportunity', **row, min_profit_wei=min_profit)
    if MODE == 'live':
        send_live(token, data, gas_limit, max_fee, gross, min_profit, round(cap_usd, 4))
    else:
        try:
            g2 = sim(data, ctx)
            log('paper_sim', result='success', gain_wei=g2, **row)
        except RuntimeError as ex:
            log('paper_sim', result='revert', err=str(ex)[:200], **row)
    return 'done'


def main():
    LOG.parent.mkdir(exist_ok=True)
    CU_FILE.parent.mkdir(exist_ok=True)
    ctx = exec_ctx()
    log('start', mode=MODE, executor=ctx[1], fee_handler=FEE_HANDLER, tokens=[r['sym'] for r in TOKENS.values()],
        idle_poll=IDLE_POLL)
    p, p_at, focus = None, 0, None
    while True:
        delay = IDLE_POLL
        try:
            if p is None or time.time() - p_at > 6 * 3600:
                p, p_at = read_params(), time.time()
                log('params', batch_wnt=p['batch'] / 1e18, impact_wnt=p['impact_wnt'], max_price_age_s=p['max_age'])
            todo, focus = ([focus] if focus else list(TOKENS)), None   # while one pot pays, only that pot is read
            for token in todo:
                now = time.time()
                if _rest.get(token, 0) > now:
                    continue
                seen = _looked.get(token)
                if seen and seen[1] == 'idle' and now - seen[0] < IDLE_POLL - 10:
                    continue                         # a near pot shortens the round; the idle ones keep their pace
                state, est = look(p, token)
                _looked[token] = (now, state)
                if state == 'near':
                    delay = min(delay, NEAR_POLL)
                if state != 'armed':
                    _armed_since.pop(token, None)
                    continue
                _armed_since.setdefault(token, now)
                res = attempt(p, token, ctx)
                if res == 'done':
                    if MODE == 'live':               # a pot can hold several batches: look at it again right away
                        focus, delay = token, ARMED_POLL
                        break
                    delay = min(delay, NEAR_POLL)
                elif res == 'unprofitable' or now - _armed_since[token] > ARMED_WINDOW:
                    _rest[token] = now + COOLDOWN    # route does not pay, or no usable report: let the others be read
                    _armed_since.pop(token, None)
                    log('rest', token=TOKENS[token]['sym'], seconds=COOLDOWN, why=res)
                else:
                    focus, delay = token, ARMED_POLL
                    break                            # keep searching reports for this token before reading the rest
        except ReadBudgetExceeded as ex:
            log('read_budget', err=str(ex))
            delay = 1800
        except Exception as ex:
            log('error', err=f'{type(ex).__name__}: {str(ex)[:300]}')
            delay = NEAR_POLL
        if delay != ARMED_POLL:
            log('next_check', delay_seconds=delay)
        time.sleep(delay)


if __name__ == '__main__':
    main()
