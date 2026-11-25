#!/usr/bin/env python3
"""trial: the Mint Club V2 bonding-curve tokens whose reserve token is HUNT (MT, DR, HEPE, ONCHAT, SIGNET) have two
prices on Base. The Bond contract mints and burns each against HUNT at the curve's step price (less a royalty of
0.1-1 pct), open to anyone; the same token trades on a hookless Uniswap v4 native-ETH pool, and HUNT itself trades on
a hookless v4 native-ETH pool. When HUNT / ETH or a token pool moves away from the curve, the round trip
  burn: WETH -> ETH -> token (v4), Bond.burn -> HUNT, HUNT -> ETH (v4) -> WETH
  mint: WETH -> ETH -> HUNT (v4), Bond.mint -> token, token -> ETH (v4) -> WETH
pays. One transaction through the BondArbV4 executor with a free Morpho flash loan of WETH; it reverts unless its
WETH + ETH balance grew by minProfit, and pays everything to the bot wallet as native ETH. No principal.
Timer bot: ONE Multicall3 eth_call every POLL seconds (the v4 slot0 of each token pool and of the HUNT pool, the
curve's price); the exact run() is simulated only for a route whose marginal round trip is above MIN_EDGE after fees."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545').rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'base'

# Addresses: Bond from the DefiLlama adapter projects/mint-club-v2 and the explorer (verified MCV2_Bond), the rest
# from the incumbent's receipt (tx 0xccb1b4fb4d6813ce...); each answered a getter on 2026-11-21 (proof.py re-checks).
BOND = '0xc5a076cad94176c2996b32d8466be1ce757faa27'        # Mint Club V2 Bond
WETH = '0x4200000000000000000000000000000000000006'
PM = '0x498581ff718922c3f8e6a244956af099b2652b2b'          # Uniswap v4 PoolManager
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'      # Morpho Blue: flashLoan, no fee
MULTICALL3 = '0xca11bde05977b3631167028862be2a173976ca11'

# Selectors and topics from `cast sig` / `cast keccak` (2026-11-21).
SEL_RUN = '0xc7bcc117'       # run((address,address,address,address,address,address,uint24,int24,uint24,int24,bool,uint256,uint256,uint256))
SEL_EXTSLOAD = '0x1e2eaeaf'  # PoolManager.extsload(bytes32)
SEL_SLOT0 = '0x3850c7bd'     # slot0()
SEL_NEXTPRICE = '0x840d885d' # Bond.priceForNextMint(address)
SEL_AGG3 = '0x82ad56cb'      # aggregate3((address,bool,bytes)[])
TOPIC_BURN = '0x80a56de61873550ae491e454783a8dfc9d08a6f8bdace0887eabd4315c4b9da8'  # Burn(address,address,address,uint256,address,uint256)
TOPIC_MINT = '0x02ed9b10d8b33a6a9fda664247bfd8f6248f74cff85cc84e56b7530c2fce560a'  # Mint(address,address,address,uint256,address,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000b00d5'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_BASE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BASE or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'
ROUTES = json.loads((HERE / 'routes.json').read_text())

POLL = 30                          # seconds between looks (one eth_call each)
MIN_EDGE = 0.002                   # marginal round trip must pay 0.2 pct after every fee before anything is simulated
SIZES = [2, 5, 10, 20, 40, 80]     # WETH flash sizes tried, in 0.001 ETH, smallest first; stops when the gain stops growing
SIZE_UNIT = 10**15
MINT_FILL = 0.995                  # mint direction: tokensToMint sized to use 99.5 pct of the reserve bought
MIN_INTEREST = 5 * 10**12          # 0.000005 ETH: smaller gains are not worth a send
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send when gross > 1.3 x the send's gas cap
TIP_SHARE_DEN = 10                 # priority fee: at most 1/10 of gross spread over the gas limit ...
TIP_MAX_WEI = 10**8                # ... and never above 0.1 gwei
MAX_FEE_CAP_WEI = 15 * 10**7       # never sign above 0.15 gwei
GAS_LIMIT_MAX = 2_400_000          # 2.4M x 0.15 gwei = 0.00036 ETH = 0.90 USD at the reference price
L1_FEE_ALLOW_WEI = 2 * 10**12      # allowance for the OP Stack L1 data fee (incumbents: about 1e-9 to 3e-7 ETH)
ETH_REF_USD = 2500.0               # USD cap reference, well above the price (about 1,670 USD on 2026-11-21)
MAX_TX_USD = 0.95
CU_CAP = 95_000
CU_COST = {'eth_call': 26, 'eth_getBlockByNumber': 20, 'eth_estimateGas': 20,
           'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10, 'eth_getLogs': 75}

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'cu.json'


class ReadBudgetExceeded(Exception):
    pass


def log(event, **fields):
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': round(time.time(), 3), 'ev': event, **fields}, separators=(',', ':')) + '\n')


def rpc(method, params, raw=False):
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(STATE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    budget['cu'] += CU_COST.get(method, 26)
    if budget['cu'] > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} CU/day cap')
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(budget))
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    import urllib.request
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as resp:
        ans = json.load(resp)
    if raw:
        return ans
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:300]}')
    return ans['result']


def w(n):
    return format(n, '064x')


def a(addr):
    return addr.lower().removeprefix('0x').zfill(64)


def agg3(calls, block='latest'):
    """aggregate3 with allowFailure = true; returns a list of (success, return bytes hex without 0x)."""
    items = []
    for target, data in calls:
        raw = data.removeprefix('0x')
        items.append(a(target) + w(1) + w(0x60) + w(len(raw) // 2) + raw + '00' * ((-(len(raw) // 2)) % 32))
    offs, pos = [], 32 * len(items)
    for it in items:
        offs.append(pos)
        pos += len(it) // 2
    data = SEL_AGG3 + w(32) + w(len(items)) + ''.join(w(o) for o in offs) + ''.join(items)
    res = rpc('eth_call', [{'to': MULTICALL3, 'data': data}, block]).removeprefix('0x')
    n = int(res[64:128], 16)
    base = 128
    out = []
    for i in range(n):
        off = int(res[base + 64 * i:base + 64 * (i + 1)], 16) * 2 + base
        ok = int(res[off:off + 64], 16) == 1
        ln = int(res[off + 128:off + 192], 16) * 2
        out.append((ok, res[off + 192:off + 192 + ln]))
    if len(out) != len(calls):
        raise RuntimeError('aggregate3: unexpected return length')
    return out


def read_state(block='latest'):
    """One eth_call: per route the slot0 of its token pool and of its reserve pool (PoolManager.extsload) and the
    curve price."""
    calls = []
    for r in ROUTES:
        calls += [(PM, SEL_EXTSLOAD + r['v4']['slot'][2:]), (PM, SEL_EXTSLOAD + r['rv4']['slot'][2:]), (BOND, SEL_NEXTPRICE + a(r['token']))]
    out = agg3(calls, block)
    state = {}
    for i, r in enumerate(ROUTES):
        (ok4, s4), (okr, sr), (okb, sb) = out[3 * i:3 * i + 3]
        if not (ok4 and okr and okb and len(s4) >= 64 and len(sr) >= 64 and len(sb) >= 64):
            continue
        sq4, fee4 = _slot0(int(s4[:64], 16))
        sqr, feer = _slot0(int(sr[:64], 16))
        price = int(sb[:64], 16)
        if sq4 and sqr and price:
            state[r['token']] = {'sq4': sq4, 'fee4': fee4, 'sqr': sqr, 'feer': feer, 'curve': price}
    return state


def _slot0(v):
    """v4 Slot0 word -> (sqrtPriceX96, swap fee in ppm: LP fee + the larger protocol fee direction)."""
    proto = (v >> 184) & 0xffffff
    return v & ((1 << 160) - 1), ((v >> 208) & 0xffffff) + max(proto & 0xfff, proto >> 12)


def _price(sq):
    return (sq / 2**96) ** 2      # raw token1 per raw token0


def edges(r, s):
    """Marginal round trips after pool fees and the royalty (floats; the executor's eth_call decides).
    Returns (burn edge, mint edge, WETH per reserve, reserve per token)."""
    tok_per_eth = _price(s['sq4'])                     # v4: currency0 = native ETH, currency1 = token
    f4 = 1 - s['fee4'] / 10**6
    weth_per_res = 1 / _price(s['sqr'])                # reserve pool: currency0 = native ETH, currency1 = reserve
    f3 = 1 - s['feer'] / 10**6
    curve = s['curve'] / 10**18                        # reserve per token (18-decimals token)
    burn = tok_per_eth * f4 * curve * (1 - r['burn_bps'] / 10**4) * weth_per_res * f3 - 1
    mint = (1 / weth_per_res) * f3 / (curve * (1 + r['mint_bps'] / 10**4)) / tok_per_eth * f4 - 1
    return burn, mint, weth_per_res, curve


def candidates(state):
    found = []
    for r in ROUTES:
        s = state.get(r['token'])
        if not s:
            continue
        burn, mint, weth_per_res, curve = edges(r, s)
        for is_mint, edge in ((False, burn), (True, mint)):
            if MIN_EDGE < edge < 5:
                found.append({'route': r, 'mint': is_mint, 'edge': edge, 'weth_per_res': weth_per_res, 'curve': curve, 'feer': s['feer']})
    found.sort(key=lambda c: -c['edge'])
    return found


def tokens_to_mint(c, amount):
    """Mint direction: the tokens the WETH `amount` buys through the reserve pool and the curve, less a margin (the
    executor sells any reserve left back). Whole tokens' worth of wei, rounded down."""
    r = c['route']
    reserve = amount / c['weth_per_res'] * (1 - c['feer'] / 10**6)
    return int(reserve / (c['curve'] * (1 + r['mint_bps'] / 10**4)) * MINT_FILL)


def run_calldata(c, amount, min_profit):
    r = c['route']
    words = [a(MORPHO), a(PM), a(BOND), a(WETH), a(r['reserve']), a(r['token']),
             w(r['v4']['fee']), w(r['v4']['ts']), w(r['rv4']['fee']), w(r['rv4']['ts']), w(1 if c['mint'] else 0), w(amount),
             w(tokens_to_mint(c, amount) if c['mint'] else 0), w(min_profit)]
    return SEL_RUN + ''.join(words)


# ---- chain access ----
def owner():
    import farmbot_signer
    result = farmbot_signer.my_address()
    address = result['address'] if isinstance(result, dict) else result
    if not isinstance(address, str) or len(address) != 42:
        raise RuntimeError('signer my_address returned no address')
    return address


def executor():
    return EXEC if MODE == 'live' else PAPER_EXEC


def call_params(data, gas_limit=None, block='latest'):
    ex = executor()
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': ex, 'data': data}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx, block]
    if MODE == 'paper':
        params.append({ex: {'code': RUNTIME_FILE.read_text().strip()}})
    return params


def gain_of(c, amount, min_profit, gas_limit=None, block='latest'):
    """Return value of the exact run() as an eth_call (wei gained); 0 when it reverts."""
    ans = rpc('eth_call', call_params(run_calldata(c, amount, min_profit), gas_limit, block), raw=True)
    if 'error' in ans or not ans.get('result') or ans['result'] == '0x':
        return 0, str(ans.get('error'))[:160]
    return int(ans['result'], 16), None


def best_size(c):
    """Try SIZES smallest first; stop when the gain stops growing. Returns (WETH amount in wei, gain in wei, error)."""
    best = (0, 0, None)
    for s in SIZES:
        gain, err = gain_of(c, s * SIZE_UNIT, 1)
        if gain <= best[1]:
            if best[1] == 0:
                best = (0, 0, err)
            break
        best = (s * SIZE_UNIT, gain, None)
    return best


def last_bond_block(token, block):
    """Block of the newest Bond burn or mint of this token near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': BOND, 'fromBlock': hex(block - 300), 'toBlock': hex(block + 10),
                               'topics': [[TOPIC_BURN, TOPIC_MINT], '0x' + a(token)]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(c, amount, gross, cap, max_fee, tip, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, run_calldata(c, amount, cap), 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', reply=reply)
        return
    receipt = None
    for _ in range(20):
        time.sleep(1.0)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    common = dict(hash=tx_hash, token=c['route']['sym'], mint=c['mint'], amount_wei=amount, expected_gross_wei=gross,
                  cap_wei=cap, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee') or '0x0', 16)
    try:
        winner = block if status else last_bond_block(c['route']['token'], block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        gross_wei=gross if status else 0, send_block=block, winner_block=winner,
        tx_index=int(receipt['transactionIndex'], 16), **common)


_dust = {}    # (token, direction) -> prices at the last look whose simulated gain was below MIN_INTEREST


def check():
    """One look: 1 eth_call when no route is above MIN_EDGE. Returns True when a gain above MIN_INTEREST was seen."""
    state = read_state()
    seen = False
    for c in candidates(state):
        r = c['route']
        s = state[r['token']]
        key = (r['token'], c['mint'])
        prices = (s['sq4'], s['sqr'], s['curve'])
        if _dust.get(key) == prices:
            continue          # same prices as the last look that was too small: no second call, no log line
        amount, gross, err = best_size(c)
        if gross < MIN_INTEREST:
            _dust[key] = prices
            log('check', result='below_interest', token=r['sym'], mint=c['mint'], edge=round(c['edge'], 5), chain_gain_wei=gross, error=err)
            continue
        seen = True
        base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
        try:
            estimate = int(rpc('eth_estimateGas', call_params(run_calldata(c, amount, 1))), 16)
        except Exception as e:
            log('simulate_revert', step='estimate', token=r['sym'], gross_wei=gross, error=str(e)[:200])
            continue
        gas_limit = estimate * 12 // 10
        tip = min(TIP_MAX_WEI, gross // TIP_SHARE_DEN // gas_limit)
        max_fee = base_fee + base_fee // 4 + tip
        cap = gas_limit * max_fee + L1_FEE_ALLOW_WEI                  # the most this send should cost = the tx's minProfit
        cap_usd = cap / 1e18 * ETH_REF_USD
        log('opportunity', token=r['sym'], mint=c['mint'], edge=round(c['edge'], 5), amount_wei=amount, gross_wei=gross,
            cap_wei=cap, base_fee=base_fee, tip_wei=tip, max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit,
            cap_usd=round(cap_usd, 4), curve=s['curve'])
        if max_fee > MAX_FEE_CAP_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
            log('opportunity_skip', reason='fee_gas_or_usd_cap', max_fee_wei=max_fee, gas_limit=gas_limit, cap_usd=cap_usd)
            continue
        if gross * SEND_MULT_DEN <= cap * SEND_MULT_NUM:              # send only when expected gross > 1.3 x this send's gas cap
            _dust[key] = prices
            log('opportunity_skip', reason='gross_below_send_line', gross_wei=gross, cap_wei=cap)
            continue
        checked, err = gain_of(c, amount, cap, gas_limit)             # the exact call that would be signed (minProfit = gas cap)
        if checked <= cap:
            log('simulate_revert', step='guard', token=r['sym'], gross_wei=gross, cap_wei=cap, error=err)
            continue
        if MODE == 'paper':
            _dust[key] = prices                                       # paper sends nothing: do not re-log the same gap
            log('paper_sim', result='success', token=r['sym'], mint=c['mint'], amount_wei=amount, gross_wei=checked,
                cap_wei=cap, gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
        else:
            send_live(c, amount, checked, cap, max_fee, tip, gas_limit)
            break                                                     # prices moved: read again before the next route
    return seen


def main():
    """Timer loop. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), bond=BOND, routes=len(ROUTES), poll_seconds=POLL)
    next_poll = 0
    looks = 0
    while True:
        try:
            now = time.time()
            if now >= next_poll:
                next_poll = now + POLL
                seen = check()
                looks += 1
                if looks % 100 == 1 and not seen:
                    log('heartbeat', looks=looks)
                if seen and MODE == 'live':
                    next_poll = time.time() + 6    # part of the gap may be left, or the send lost: look again soon
            else:
                time.sleep(max(0.5, min(30, next_poll - now)))
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            time.sleep(86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 5)   # to 00:00 UTC
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            next_poll = time.time() + POLL
            time.sleep(5)


if __name__ == '__main__':
    main()
