#!/usr/bin/env python3
"""trial-gmx-buyback-avalanche: take one GMX v2 FeeHandler buyback batch on Avalanche when it pays.

GMX's FeeHandler sells the protocol's accrued USDC fees to anyone: pay one batch (150 WAVAX) and receive USDC at the
oracle price plus 0.6 pct, capped by the amount available. The bot reads the pot on a timer. When the pot is worth more
than a batch plus costs it looks for signed price reports (Chainlink Data Streams) for WAVAX and USDC in the calldata of
a GMX keeper transaction that is already confirmed, no older than MAX_REPORT_AGE, builds the executor call (flash 150
WAVAX, claimFees, buyback, sell the USDC, repay), simulates it and, if the simulated gain exceeds the signed gas cap,
sends it (BOT_MODE=live) or logs a paper simulation (BOT_MODE=paper). The executor reverts unless its wrapped-native
balance grew by minProfit, so a lost attempt costs gas only. Confirmed chain data only: no pending transactions.
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
CHAIN = 'avalanche'

# Addresses: gmx-io/gmx-synthetics deployments/avalanche/*.json and the trace of take 0x2c36270a... (README).
FEE_HANDLER = '0x1a3a103f9f536a0456c9b205152a3ac2b3c54490'
DATA_STORE = '0x2f0b22339414aded7d5f06f9d604c7ff5b2fe3f6'
EVENT_EMITTER = '0xdb17b211c34240b014ab6d61d4a31fa0c0e20c26'
STREAM_PROVIDER = '0x236913dbd610d9d77b9b8b62c99af0ff4e43ce3a'   # Data Streams oracle provider used by the takers
VAULT = '0xba12222222228d8ba445958a75a0704d566bf2c8'              # Balancer V2 vault, flash fee 0
WNT = '0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7'                # WAVAX
USDC = '0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e'               # native USDC, 6 decimals
POOL = '0xfae3f424a0a47706811521e3ee268f00cfb5c45e'               # Uniswap V3 WAVAX/USDC 0.05 pct (token0 = WAVAX)
MARKETS = (   # every market the four takes of 2026-11-11..18 claimed USDC fees from
    '0xb7e69749e3d2edd90ea59a4932efea2d41e245d7', '0x913c1f46b48b3ed35e7dc3cf754d4ae8499f31cf',
    '0xfb02132333a79c8b5bd0b64e3abcca5f7faf2937', '0xd2efd1ea687cd78c41ac262b3bc9b53889ff1f70',
    '0xd1cf931fa12783c1dd5abb77a0706c27cf352f25', '0x94ce6f65188a92f297c7f0a5a7b3cad9013450f8',
    '0x8970b527e84aa17a33d38b65e9a5ab5817fc0027', '0xa74586743249243d3b77335e15fe768ba8e1ec5a',
)
# selectors, topics and DataStore keys from cast (scratch/trial-gmx-buyback-avalanche/consts.py)
SEL_TAKE = '0x1558ca12'
SEL_OUT = '0x4a6f4d0e'       # getOutputAmount(address[],address,address,uint256,uint256,uint256)
SEL_SLOT0 = '0x3850c7bd'
SEL_GETUINT = '0xbd02d0f5'
TOPIC_EVENTLOG = '0x7e3bde2ba7aca4a8499608ca57f3b0c1c1c93ace63ffd3741a9fab204146fc9a'   # EventLog, read from a receipt
TOPIC_ORACLE = '0x41c7b30afab659d385f1996d0addfa6e647694862e72378d0b43773f556cbeb2'     # keccak(OraclePriceUpdate)
TOPIC_BUYBACK = '0x5cdc95df4470fa1587194a1e5697177a1ab16df1d46f3f34a2eff0a318b23c84'    # keccak(BuybackFees)
KEY_MAX_AGE = '0xfa1b96b222839b1092d70683ece9286144deafaed9bf70a32ca82a4338f5d299'
KEY_BATCH_WNT = '0x84ffc4cd72504ed2966e3fec63eebd1abfe0e7d4f991c49794f2beb1ef0c64fc'
KEY_IMPACT_WNT = '0x85ed5e0b66991084f08176fdf02e2c61419d96f387aa6d57554f4f06341ed291'
KEY_IMPACT_USDC = '0xdec03c9ed8f12d028fab01437507943fc3acf628aaa70be81353fa6095b4658c'

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_AVALANCHE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_AVALANCHE or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

IDLE_POLL = 300          # s between pot reads while the pot is far below a batch
NEAR_POLL = 60           # s while the pot is within 10 pct of paying
ARMED_POLL = 6           # s between report searches while the pot pays
NEAR_RATIO = 0.90
SWAP_FEE = 0.0005
MIN_EST_GAIN_WNT = 0.05  # arm when the estimated gain is above this (about 0.35 USD, above any gas cap the bot signs)
MAX_REPORT_AGE = 20      # s; the FeeHandler allows BUYBACK_MAX_PRICE_AGE (30 s) at inclusion
REPORT_LOOKBACK = 40     # blocks searched for confirmed keeper txs (about 35-60 s)
SIM_GAS = 5_000_000
GAS_LIMIT_MAX = 4_000_000
GAS_MARGIN = 1.25
TIP_WEI = 2_000_000_000              # 2 nAVAX per gas; the takers of 11-11..18 paid 1 nAVAX
MAX_FEE_CEIL = 60_000_000_000        # refuse to sign above 60 nAVAX per gas
MAX_CAP_USD = 0.90                   # refuse a send whose gasLimit x maxFeePerGas is worth more (manifest: 1 USD)
RELAY_CU_CAP = 90_000
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_blockNumber': 10, 'eth_getBlockByNumber': 16, 'eth_estimateGas': 87,
           'eth_getTransactionByHash': 17, 'eth_getTransactionReceipt': 15}

LOG = HERE / 'logs' / 'bot.jsonl'
CU_FILE = HERE / 'state' / 'cu.json'
_id = 0
_parsed = {}


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


def take_calldata(batch, tokens, providers, datas, min_profit, min_out=1):
    """take(Plan,uint256); Plan = (vault, feeHandler, weth, batch, feeToken, markets[], minOut, prices, swapPool).
    Checked byte for byte against cast calldata (scratch/trial-gmx-buyback-avalanche/selftest.py)."""
    markets = enc_addrs(MARKETS)
    plan = (aword(VAULT) + aword(FEE_HANDLER) + aword(WNT) + word(batch) + aword(USDC) + word(9 * 32) + word(min_out)
            + word(9 * 32 + len(markets) // 2) + aword(POOL) + markets + enc_prices(tokens, providers, datas))
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


def pot_usdc():
    """available USDC + the WNT share of every listed market's claimable USDC fees, uncapped (prices 1 and 1e30)."""
    data = (SEL_OUT + word(6 * 32) + aword(USDC) + aword(WNT) + word(2) + word(1) + word(10**30) + enc_addrs(MARKETS))
    return int(rpc('eth_call', [{'to': FEE_HANDLER, 'data': data}, 'latest']), 16)


def avax_usd():
    """USDC per WAVAX from slot0 of the pool the route sells into (token0 = WAVAX 18 dec, token1 = USDC 6 dec)."""
    sqrt_p = int(rpc('eth_call', [{'to': POOL, 'data': SEL_SLOT0}, 'latest'])[2:66], 16)
    return sqrt_p * sqrt_p * 10**12 / 2**192


def parse_prices(inp):
    """A keeper call is fn(bytes32 key, (address[] tokens, address[] providers, bytes[] data)). Returns
    {token: (provider, data_hex)} or {} if the calldata does not have that shape."""
    try:
        b = bytes.fromhex(inp[10:])
        u = lambda o: int.from_bytes(b[o:o + 32], 'big')
        t = u(32)
        if t % 32 or t + 96 > len(b):
            return {}
        o_tok, o_prov, o_dat = t + u(t), t + u(t + 32), t + u(t + 64)
        n = u(o_tok)
        if not 0 < n <= 20 or u(o_prov) != n or u(o_dat) != n:
            return {}
        out = {}
        for i in range(n):
            tok = '0x' + b[o_tok + 32 + 32 * i + 12:o_tok + 64 + 32 * i].hex()
            prov = '0x' + b[o_prov + 32 + 32 * i + 12:o_prov + 64 + 32 * i].hex()
            o = o_dat + 32 + u(o_dat + 32 + 32 * i)
            ln = u(o)
            if o + 32 + ln > len(b):
                return {}
            out[tok] = (prov, b[o + 32:o + 32 + ln].hex())
        return out
    except Exception:
        return {}


def report_ts(data_hex):
    """observationsTimestamp of a Data Streams report: abi (bytes32[3] context, bytes blob, ...); blob word 2."""
    raw = bytes.fromhex(data_hex)
    off = int.from_bytes(raw[96:128], 'big')
    if off + 128 > len(raw):
        return 0
    return int.from_bytes(raw[off + 32 + 64:off + 32 + 96], 'big')


def fresh_reports(head):
    """Newest confirmed WAVAX and USDC reports from GMX keeper txs in the last REPORT_LOOKBACK blocks."""
    logs = rpc('eth_getLogs', [{'address': EVENT_EMITTER, 'fromBlock': hex(head - REPORT_LOOKBACK), 'toBlock': hex(head),
                                'topics': [None, TOPIC_ORACLE]}])
    txs = {}
    for l in logs:
        if len(l['topics']) > 2 and '0x' + l['topics'][2][26:] in (WNT, USDC):
            txs.setdefault(l['transactionHash'], set()).add('0x' + l['topics'][2][26:])
    best = {}
    for h in sorted(txs, key=lambda h: -int([l for l in logs if l['transactionHash'] == h][0]['blockNumber'], 16))[:3]:
        if h not in _parsed:                      # each keeper tx is fetched once
            if len(_parsed) > 200:
                _parsed.clear()
            _parsed[h] = parse_prices(rpc('eth_getTransactionByHash', [h]).get('input', '0x'))
        for tok, (prov, data) in _parsed[h].items():
            # Keepers pass the same Chainlink report bytes under their own handler's provider (0x048ee03a...); the
            # FeeHandler's oracle wants STREAM_PROVIDER for these tokens and accepts the bytes (lifttest.py).
            if tok in (WNT, USDC) and len(data) >= 600:
                ts = report_ts(data)
                if ts > best.get(tok, (0,))[0] and ts <= time.time() + 5:
                    best[tok] = (ts, STREAM_PROVIDER, data, h)
        if WNT in best and USDC in best:
            break
    return best


def winner(send_block, our_hash):
    """Block and tx of the newest BuybackFees event near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': EVENT_EMITTER, 'fromBlock': hex(max(0, send_block - 2000)), 'toBlock': hex(head),
                                'topics': [TOPIC_EVENTLOG, TOPIC_BUYBACK]}])
    if not logs:
        return None, None
    ours = [l for l in logs if l['transactionHash'].lower() == our_hash.lower()]
    last = ours[0] if ours else max(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(last['blockNumber'], 16), last['transactionHash']


def send_live(data, gas_limit, max_fee, gross, min_profit, cap_usd):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=TIP_WEI)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply)   # final, never retried
        return
    log('send', hash=h, gas_limit=gas_limit, max_fee=max_fee, priority=TIP_WEI, gross_wei=gross, min_profit_wei=min_profit,
        gas_cap_usd=cap_usd, executor=EXEC)
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
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16), send_block=b, winner_block=wb, winner_tx=wtx,
        blocks_after_winner=(b - wb if wb is not None else None), gross_wei=gross)


def read_params():
    p = {'batch': get_uint(KEY_BATCH_WNT), 'max_age': get_uint(KEY_MAX_AGE),
         'premium': (get_uint(KEY_IMPACT_WNT) + get_uint(KEY_IMPACT_USDC)) / 1e30}
    if not 10**18 <= p['batch'] <= 2000 * 10**18 or p['premium'] > 0.05:
        raise RuntimeError(f'implausible buyback parameters {p}')
    return p


def look(p):
    """One pot read. Returns (state, estimated gain in WNT)."""
    pot, px = pot_usdc(), avax_usd()
    batch = p['batch'] / 1e18
    cap = batch * px * (1 + p['premium'])                      # USDC the buyback pays at most (pool price as a proxy)
    out = min(pot / 1e6, cap)
    est = out * (1 - SWAP_FEE) / px - batch                    # WNT left after selling the USDC and repaying the batch
    need = batch * px / (1 - SWAP_FEE)
    ratio = pot / 1e6 / need
    state = 'armed' if est >= MIN_EST_GAIN_WNT else ('near' if ratio >= NEAR_RATIO else 'idle')
    log('check', pot_usdc=pot / 1e6, avax_usd=round(px, 4), cap_usdc=round(cap, 2), est_gain_wnt=round(est, 4),
        ratio=round(ratio, 4), state=state)
    return state, est, px


def attempt(p, px, ctx):
    """Pot pays by the estimate: find fresh confirmed reports, simulate, send. Returns True if a send or paper sim ran."""
    head = int(rpc('eth_blockNumber', []), 16)
    best = fresh_reports(head)
    now = time.time()
    if WNT not in best or USDC not in best:
        log('no_reports', head=head, have=sorted(best))
        return False
    age = now - min(best[WNT][0], best[USDC][0])
    if age > MAX_REPORT_AGE or age > p['max_age'] - 5:
        log('reports_stale', head=head, age_s=round(age, 1), wnt_tx=best[WNT][3], usdc_tx=best[USDC][3])
        return False
    toks, provs, datas = [USDC, WNT], [best[USDC][1], best[WNT][1]], [best[USDC][2], best[WNT][2]]
    try:
        gross = sim(take_calldata(p['batch'], toks, provs, datas, 1), ctx)
    except ReadBudgetExceeded:
        raise
    except RuntimeError as ex:
        log('simulate_revert', head=head, age_s=round(age, 1), err=str(ex)[:200])
        return False
    base = int(rpc('eth_getBlockByNumber', ['latest', False]).get('baseFeePerGas', '0x0'), 16)
    max_fee = int(base * 1.3) + TIP_WEI
    try:
        gas_limit = int(estimate(take_calldata(p['batch'], toks, provs, datas, 1), ctx) * GAS_MARGIN)
    except ReadBudgetExceeded:
        raise
    except RuntimeError as ex:
        log('estimate_revert', head=head, err=str(ex)[:200])
        return False
    cap_wei = gas_limit * max_fee
    cap_usd = cap_wei / 1e18 * px
    row = dict(head=head, report_age_s=round(age, 1), report_tx_wnt=best[WNT][3], report_tx_usdc=best[USDC][3], gross_wei=gross,
               gas_limit=gas_limit, max_fee=max_fee, cap_wei=cap_wei, gas_cap_usd=round(cap_usd, 4))
    if gas_limit > GAS_LIMIT_MAX or max_fee > MAX_FEE_CEIL or cap_usd > MAX_CAP_USD:
        log('skip_gas_cap', **row)
        return False
    if gross <= cap_wei:                      # trial rule: send only when the expected gross exceeds the send's gas cap
        log('skip_gross_below_cap', **row)
        return False
    min_profit = cap_wei + 1
    data = take_calldata(p['batch'], toks, provs, datas, min_profit)
    log('opportunity', **row, min_profit_wei=min_profit)
    if MODE == 'live':
        send_live(data, gas_limit, max_fee, gross, min_profit, round(cap_usd, 4))
    else:
        try:
            g2 = sim(data, ctx)
            log('paper_sim', result='success', gain_wei=g2, **row)
        except RuntimeError as ex:
            log('paper_sim', result='revert', err=str(ex)[:200], **row)
    return True


def main():
    LOG.parent.mkdir(exist_ok=True)
    CU_FILE.parent.mkdir(exist_ok=True)
    ctx = exec_ctx()
    log('start', mode=MODE, executor=ctx[1], fee_handler=FEE_HANDLER, markets=len(MARKETS), idle_poll=IDLE_POLL)
    p, p_at = None, 0
    while True:
        delay = IDLE_POLL
        try:
            if p is None or time.time() - p_at > 6 * 3600:
                p, p_at = read_params(), time.time()
                log('params', batch_wnt=p['batch'] / 1e18, premium=p['premium'], max_price_age_s=p['max_age'])
            state, est, px = look(p)
            if state == 'armed':
                done = attempt(p, px, ctx)
                delay = NEAR_POLL if done else ARMED_POLL
            elif state == 'near':
                delay = NEAR_POLL
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
