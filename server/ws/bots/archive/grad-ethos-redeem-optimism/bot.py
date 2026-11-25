"""grad-ethos-redeem-optimism: ERN below-par redemption on Ethos Reserve (OP Mainnet), one atomic executor call.

Graduated from trial-ethos-redeem-optimism (same executor bytecode, same fee). Two changes, both from the
trial's live record (README): the flash-loan size sweep continues above 40 USDC while the simulated gain still
grows (up to 400), and after a won send the bot checks again at once instead of waiting 60 s.

Waits on the feed for Sync events of the Velodrome ERN/USDC pool (plus a 600 s safety poll; on a feed gap or
error it re-reads state at once), simulates the executor
take() for a few flash-loan sizes and, when the simulated USDC gain exceeds the signed gas cap, sends it
(BOT_MODE=live) or logs a paper simulation (BOT_MODE=paper). The executor reverts unless its USDC balance grows
by minProfit, so a lost attempt costs gas only.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.append('/opt/farm/lib')   # farmbot_signer lives here; the live service does not add it

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'optimism'
FEED = 'http://127.0.0.1:8546/logs/optimism'

# Addresses: read from the incumbent's take 0x33f6f2be... (debug_traceTransaction) and getters, see README.
VAULT = '0xba12222222228d8ba445958a75a0704d566bf2c8'    # Balancer V2 Vault (flash lender, 0 fee)
USDC = '0x0b2c639c533813f4aa9d7837caf62653d097ff85'     # native USDC, 6 decimals
POOL = '0x605cce502dee6bd201b493782e351e645d44abbb'     # Velodrome ERN/USDC pool
ERN = '0xc5b001dc33727f8f26880b184090d3e252470d45'
TM = '0x75c72f459f2054b46cefd6d10ec99d0fbd777f05'       # Ethos TroveManager v2.1
HELPER = '0x5dc932a9a35026bc715a1be2669d92ac3e3867c3'   # RedemptionHelper (sortedTroves() getter)
PRICE_FEED = '0xadd6f326a395629926d9a535d809b5e3d8c7fe8d'
WETH = '0x4200000000000000000000000000000000000006'
ROUTER = '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45'   # Uniswap SwapRouter02
SELL_FEE = 500
MAX_ITER = 20
SYNC_TOPIC = '0xcf2aa50876cdfbb541206f89af0ee78d44a2abf8d328e37fa4917f982149848a'       # Sync(uint256,uint256)
REDEEM_TOPIC = '0x08b6f1ce3f9ab2722e8ea40c31a3e3a806a41702c5994f29af43dc0c1f2837df'     # TM Redemption event
# take((address,address,uint256,address,address,address,address,address,address,uint256,address,uint24),uint256)
SEL_TAKE = '0xd52c804c'

PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_OPTIMISM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_OPTIMISM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

# ---- loss guard -----------------------------------------------------------------------------
MAX_TX_USD = 0.90              # signed gas cap (maxFee x gasLimit + L1 allowance) stays under this
MAX_FEE_WEI = 100_000_000      # 0.1 gwei absolute ceiling for maxFeePerGas
MAX_GAS_LIMIT = 2_000_000
L1_ALLOWANCE_WEI = 100_000_000_000   # 6x the incumbent's measured l1Fee (1.51e10 wei, tx 0x33f6f2be...)
TIP_WEI = 2_000_000            # incumbents bid 1,000,000 wei (0.001 gwei)
BID_SHARE = 0.15               # priority fee x gasLimit never exceeds this share of the simulated gross
SIZES_USDC = (5, 10, 15, 20, 25, 30, 40)   # flash-loaned, never the bot's own funds
# Tried only when the gain is still growing at the top of SIZES_USDC, and only while it keeps growing.
# Fork, parent of the trial's 40 USDC win (block 159938191): 40 -> 2.04, 80 -> 3.16, 120 -> 3.44, 200 -> 1.78 USDC.
EXTRA_SIZES_USDC = (60, 80, 120, 160, 240, 320, 400)
MAX_FOLLOW_UPS = 8             # checks in a row after a won send (the rival took 6 more in 20 blocks, 11-23)
LOSS_COOLDOWN = 10             # seconds without sending after a lost send
PROBE_USDC = 5
# Safety poll. The trial's 120 s timer made 1,954 checks (152k CU, 0.08 USD) for 0.054 USDC of wins in 105 h
# (scratch/grad-ethos-redeem-optimism/realized.json), so the grad keeps only the feed rule's 10 min poll.
POLL_INTERVAL = 600
SYNC_SPACING = 10              # seconds between two Sync-triggered checks; a Sync inside it is checked when it ends
FEED_BACKOFF = (30, 60, 120)   # seconds to wait after the 1st, 2nd, 3rd+ feed error in a row (state is re-read first)
SEND_COOLDOWN = 60
RELAY_CU_CAP = 60_000          # per UTC day; the feed's own CU is metered separately
TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'   # Transfer(address,address,uint256)
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
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
        raise RuntimeError(f'{method}: {str(ans["error"])[:300]}')
    return ans['result']


def word(n):
    return format(n, '064x')


def aword(a):
    return a.lower().removeprefix('0x').zfill(64)


def addr_of(h):
    return '0x' + h[-40:].lower()


def call(to, data):
    return rpc('eth_call', [{'to': to, 'data': data}, 'latest'])


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


def calldata(borrower, amount, min_profit):
    # the Route struct is all static words, so the tuple is encoded in place
    return (SEL_TAKE + aword(VAULT) + aword(USDC) + word(amount) + aword(POOL) + aword(ERN) + aword(TM)
            + aword(PRICE_FEED) + aword(WETH) + aword(borrower) + word(MAX_ITER) + aword(ROUTER) + word(SELL_FEE)
            + word(min_profit))


def sim(data, ctx, gas=MAX_GAS_LIMIT):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data, 'gas': hex(gas)}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_call', params)[2:66], 16)


def try_sim(data, ctx, gas=MAX_GAS_LIMIT):
    try:
        return sim(data, ctx, gas)
    except ReadBudgetExceeded:
        raise
    except RuntimeError:
        return None    # executor revert: NoProfit or nothing to redeem


def estimate(data, ctx):
    frm, to, ov = ctx
    params = [{'from': frm, 'to': to, 'data': data}, 'latest'] + ([ov] if ov else [])
    return int(rpc('eth_estimateGas', params), 16)


_sorted_troves = None


def lowest_trove():
    global _sorted_troves
    if _sorted_troves is None:       # read once per process, inside the main loop's handlers
        a = addr_of(call(HELPER, '0xae918754'))                       # sortedTroves()
        if int(a, 16) == 0:
            raise RuntimeError('sortedTroves() returned zero')
        _sorted_troves = a
    return addr_of(call(_sorted_troves, '0x76082715' + aword(WETH)))  # getLast(collateral)


def eth_usd():
    return int(call(PRICE_FEED, '0xace1798e' + aword(WETH)), 16) / 1e18   # fetchPrice(collateral), read by eth_call


def winner_block(send_block, our_hash):
    """Block of the Redemption event near our send (ours if we won)."""
    head = int(rpc('eth_blockNumber', []), 16)
    logs = rpc('eth_getLogs', [{'address': TM, 'fromBlock': hex(max(0, send_block - 300)), 'toBlock': hex(head),
                                'topics': [REDEEM_TOPIC]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours), None
    if not logs:
        return None, None
    last = max(logs, key=lambda x: int(x['blockNumber'], 16))
    return int(last['blockNumber'], 16), last['transactionHash']


def send_live(data, gas_limit, max_fee, tip, gross, min_profit, cap_usd, amount):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=max(1, tip))
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply, amount_usdc=amount)   # final, never retried
        return None, None
    log('send', hash=h, amount_usdc=amount, gas_limit=gas_limit, max_fee=max_fee, priority=tip, gross_usdc=gross,
        min_profit_usdc=min_profit, gas_cap_usd=cap_usd, executor=EXEC)
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
        return None, None
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16) + int(receipt.get('l1Fee') or '0x0', 16)
    # What the wallet really received: USDC Transfer logs to the bot wallet in the receipt. The simulated gross
    # (sim_gross_usdc) was read before the send and can differ (trial: 3.05 simulated against 2.30 received).
    realized = None
    try:
        me = bot_address().lower()[2:]
        realized = sum(int(l['data'], 16) for l in receipt.get('logs') or []
                       if l['address'].lower() == USDC and l['topics'][0].lower() == TRANSFER_TOPIC
                       and len(l['topics']) == 3 and l['topics'][2][-40:].lower() == me)
    except Exception:
        realized = None
    try:
        wb, wtx = winner_block(b, h)
    except Exception:
        wb, wtx = None, None
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost, send_block=b,
        winner_block=wb, winner_tx=wtx, blocks_after_winner=(b - wb if wb is not None else None),
        realized_usdc=realized, sim_gross_usdc=gross, amount_usdc=amount)
    return ('won' if status else 'lost'), b


def check_loop(s, trigger):
    """One check; after a won send check again at once (at most MAX_FOLLOW_UPS times), since more may be left."""
    for i in range(MAX_FOLLOW_UPS + 1):
        if check(s, trigger if i == 0 else 'after_win') != 'won':
            break


def check(s, trigger):
    now = time.time()
    s['last_check'] = now
    ctx = exec_ctx()
    borrower = lowest_trove()
    if int(borrower, 16) == 0:
        log('check', trigger=trigger, reason='no_trove')
        return
    probe = try_sim(calldata(borrower, PROBE_USDC * 10**6, 0), ctx)
    if not probe:
        log('check', trigger=trigger, borrower=borrower, probe_gain=probe, reason='nothing_to_take')
        return
    # The gain rises with the size and then falls (README section 4), so go up only while it keeps growing:
    # an ordinary 5 USDC case costs one more eth_call, not six.
    rows = {PROBE_USDC: probe}
    amount, gross = PROBE_USDC, probe
    for size in SIZES_USDC + EXTRA_SIZES_USDC:
        if size <= PROBE_USDC:
            continue
        rows[size] = try_sim(calldata(borrower, size * 10**6, 0), ctx)
        if not rows[size] or rows[size] <= gross:
            break
        amount, gross = size, rows[size]
    price = eth_usd()
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    try:
        gas_limit = min(MAX_GAS_LIMIT, estimate(calldata(borrower, amount * 10**6, 0), ctx) * 5 // 4)
    except RuntimeError as e:
        log('opportunity_skip', reason='estimate_revert', error=str(e)[:160], amount_usdc=amount, gross_usdc=gross)
        return
    gross_usd = gross / 1e6
    tip = min(TIP_WEI, int(gross_usd * BID_SHARE / price * 1e18 / gas_limit))   # bid <= BID_SHARE of gross
    max_fee = base_fee * 2 + tip
    cap_wei = gas_limit * max_fee + L1_ALLOWANCE_WEI
    cap_usd = cap_wei / 1e18 * price
    min_profit = int(cap_usd * 1e6) + 1          # a win always pays more than the signed gas cap
    log('opportunity', trigger=trigger, borrower=borrower, sweep=rows, amount_usdc=amount, gross_usdc=gross,
        gross_usd=gross_usd, eth_usd=price, base_fee=base_fee, gas_limit=gas_limit, max_fee=max_fee, priority=tip,
        gas_cap_usd=cap_usd, min_profit_usdc=min_profit)
    if max_fee > MAX_FEE_WEI or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_or_usd_cap', max_fee=max_fee, gas_cap_usd=cap_usd)
        return
    if gross_usd <= cap_usd or gross < min_profit:
        log('opportunity_skip', reason='gross_below_gas_cap', gross_usd=gross_usd, gas_cap_usd=cap_usd)
        return
    if s.get('cooldown_until', 0) > now:
        log('opportunity_skip', reason='cooldown')
        return
    data = calldata(borrower, amount * 10**6, min_profit)
    checked = try_sim(data, ctx, gas_limit)      # the exact guarded call at the signed gas limit
    if not checked:
        log('simulate_revert', amount_usdc=amount, min_profit_usdc=min_profit, gas_limit=gas_limit)
        return
    s['cooldown_until'] = now + SEND_COOLDOWN
    if MODE == 'live':
        outcome, block = send_live(data, gas_limit, max_fee, tip, checked, min_profit, cap_usd, amount)
        if outcome == 'won':
            # more may be left (11-23: the rival took 4.35 USDC in the 18 blocks after the trial's one take).
            # Wait until the relay's head includes our take, then the caller checks again at once.
            s['cooldown_until'] = 0
            for _ in range(5):
                if int(rpc('eth_blockNumber', []), 16) >= block:
                    break
                time.sleep(0.5)
            return 'won'
        if outcome == 'lost':
            s['cooldown_until'] = time.time() + LOSS_COOLDOWN
    else:
        log('paper_sim', result='success', amount_usdc=amount, gross_usdc=checked, min_profit_usdc=min_profit,
            gas_limit=gas_limit, max_fee=max_fee, priority=tip, gas_cap_usd=cap_usd,
            net_usd_at_cap=checked / 1e6 - cap_usd)


def load_state():
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {'feed_cursor': None, 'last_check': 0, 'cooldown_until': 0}


def save_state(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, separators=(',', ':')))
    tmp.replace(STATE)


def feed_wait(cursor, wait=55):
    q = {'address': POOL, 'topic0': SYNC_TOPIC, 'timeout': str(wait)}
    if cursor:
        q['after'] = cursor
    with urllib.request.urlopen(FEED + '?' + urllib.parse.urlencode(q), timeout=wait + 10) as r:
        return json.load(r)


def main():
    s = load_state()
    log('start', mode=MODE, executor=(EXEC if MODE == 'live' else PAPER_EXEC), pool=POOL, trove_manager=TM,
        poll_seconds=POLL_INTERVAL)
    pending = False     # a Sync arrived inside SYNC_SPACING and still has to be checked
    feed_errors = 0     # feed errors in a row
    while True:
        try:
            if time.time() - s.get('last_check', 0) >= POLL_INTERVAL:
                check_loop(s, 'timer')
                pending = False
            save_state(s)
            wait = 55
            if pending:     # wake when the spacing ends, so no Sync is left unchecked until the timer
                wait = max(1, min(55, int(SYNC_SPACING - (time.time() - s.get('last_check', 0))) + 1))
            result = feed_wait(s.get('feed_cursor'), wait)
            feed_errors = 0
            s['feed_cursor'] = result.get('cursor', s.get('feed_cursor'))
            if result.get('gap'):
                # the stream was interrupted: a Sync may be missing, so re-read state now, with no spacing
                check_loop(s, 'gap')
                pending = False
            else:
                if result.get('logs'):
                    pending = True
                if pending and time.time() - s.get('last_check', 0) >= SYNC_SPACING:
                    check_loop(s, 'pool_sync')
                    pending = False
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError) as e:
            # 429 / 503 / connection error: a Sync may be missing. Re-read state now, then back off and resume.
            feed_errors += 1
            log('feed_error', error=str(e)[:180], in_a_row=feed_errors)
            try:
                check_loop(s, 'feed_error')
                pending = False
            except ReadBudgetExceeded as e2:
                log('read_budget', error=str(e2))
                time.sleep(600)
            except Exception as e2:
                log('check_error', error=str(e2)[:180])
            time.sleep(FEED_BACKOFF[min(feed_errors, len(FEED_BACKOFF)) - 1])
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(5)
        save_state(s)


if __name__ == '__main__':
    main()
