#!/usr/bin/env python3
"""Trial: leveraged tokens (HYPE5L, HYPE3L, xyz:NVDA5L, BTC5L; LeveragedToken v1.2.1) NAV versus their Hyperswap V2 pair.

Each token has a public mint(to, usdc, minOut) with no fee and a public redeem(to, amount, minBase) with a fee of
0.3 % x leverage, both at a NAV read from HyperCore. The tokens also trade on Hyperswap V2 pairs (against ALT or
USDC). When the NAV has moved away from the pair price by more than the fees, one transaction through the LtArb
executor flash-borrows USDC from Morpho Blue and either mints straight into the pair and takes the other side
(ALT is sold for USDC on its 1 % V3 pool), or buys the token on the pair and redeems it, repays, and pays the USDC
gain to the bot wallet. The executor reverts unless the gain is at least minProfit, so a lost attempt costs gas only.

The NAV moves with the perp price every block and has no event, so the bot polls on a timer: one eth_call of the
executor's probe() (all candidates in one call) every POLL_S seconds.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'hyperevm'

# Route targets: all are call arguments of the executor (getters: scratch/r403a/probe.py, pools.py, pairs.py)
MORPHO = '0x68e37de8d93d3496ae143f2e900490f6280c57cd'        # Morpho Blue (flash lender, no fee)
USDC = '0xb88339cb7199b77e23db6e890353e22632ba630f'          # HyperEVM USDC, 6 decimals (the tokens' base asset)
ALT = '0xa3882d42ed12b57c10c85e8ec8febd0774600000'           # the protocol's token, HYPE5L's main pair partner
V3_ALT_USDC = '0xc2065d7ca9c8c612334eccbc5abc4de57097e45a'   # ALT/USDC 1 % V3 pool (factory 0xff7b3e8c...)
ZERO = '0x0000000000000000000000000000000000000000'
V2_FEE_BPS = 30                                              # Hyperswap V2 pair fee (factory 0x724412c0...)
# name: (leveraged token, V2 pair, mid token, V3 pool mid/USDC or ZERO, USDC sizes)
ROUTES = {
    'HYPE5L-ALT': ('0x18b8539261cf9e760e7fec4a8a73c50f0ae7babe', '0x4e3e10d8dcaa19b830df71d16528027ec106ee77', ALT, V3_ALT_USDC, [10, 15, 20]),   # the ALT/USDC V3 pool is shallow: 40 USDC already loses to 10
    'HYPE5L-USDC': ('0x18b8539261cf9e760e7fec4a8a73c50f0ae7babe', '0x0dc5ff5ee49525ce100868184f355929c41c7882', USDC, ZERO, [10]),
    'HYPE3L-USDC': ('0x9a51b0dc3545cb8e9b0382b42c91f9e39a92efd6', '0xe1607fd124f254b5f4b58887ca87d1fa8c2fcfc5', USDC, ZERO, [10]),
    'NVDA5L-USDC': ('0xae3782e28f34dd4d12395187f2e0cb3444fcc3c8', '0xf4b2c1e258a3a24d3a195469512ac8d62d4e87d0', USDC, ZERO, [10]),
    'BTC5L-USDC': ('0xbe4e97a8fceeb1b82d64349fba6ff29b65ad3b7d', '0x2cfdbba775e0d4b0b9cca857ab746a99d944c073', USDC, ZERO, [10]),
}
POOL_WHYPE = '0xbd19e19e4b70eb7f248695a42208bc1edbbfb57d'    # WHYPE/USDT0 0.05%, token0 WHYPE: HYPE price for the gas cap
SEL_RUN = '0x2eb19bdb'       # cast sig run((address,address,address,address,uint256,address,address,bool,uint256,uint256,uint256,uint256))
SEL_PROBE = '0x5c2e166c'     # cast sig probe((address,address,address,address,uint256,address,address,bool,uint256,uint256,uint256,uint256)[])
SEL_SLOT0 = '0x3850c7bd'     # cast sig slot0()
T_MINT = '0x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee'     # cast keccak Mint(address,address,uint256,uint256)
T_REDEEM = '0x3f693fff038bb8a046aa76d9516190ac7444f7d69cf952c4cbdc086fdef2d6fc'   # cast keccak Redeem(address,address,uint256,uint256)

PAPER_OWNER = '0x1111111111111111111111111111111111111111'   # the owner baked into the fork deployment (immutable)
PAPER_EXEC = '0x00000000000000000000000000000000000a7b01'    # arbitrary codeless address; paper code override only
EXEC = os.environ.get('EXECUTOR_ADDR_HYPEREVM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_HYPEREVM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
CU_FILE.parent.mkdir(exist_ok=True)

# ---- loss guard (trial rule: every send's gas limit x maxFeePerGas < 1 USD) ----
GAS_LIMIT_MAX = 1_900_000      # chain cap 2,000,000
GAS_LIMIT_FALLBACK = 900_000   # used only if eth_estimateGas fails (paper); live never sends without an estimate
GAS_MARGIN = 1.2               # incumbent takes use 265k-340k gas (inventory); the flash route about 450k-600k
MAX_FEE_WEI = 2 * 10**9        # hard ceiling on maxFeePerGas: 1.9M x 2 gwei = 0.0038 HYPE
SEND_CAP_USD = 0.95            # the gas cap valued at the pool HYPE price x 1.15 must stay under this
HYPE_MARGIN = 1.15
BID_SHARE = 0.40               # priority fee bid is at most 40% of simulated gross (the incumbents pay 50-80%)
GAIN_OVER_CAP = 1.5            # send only if the simulated gain is at least 1.5 x this send's gas cap
MIN_GAIN_UNITS = 15_000        # 0.015 USDC: smaller probe gains are not evaluated at all (saves 62 CU per thin gap)
POLL_S = 27                    # one probe eth_call per poll: 3,200 polls/day x 26 CU = 83,200 CU
COOLDOWN_S = 5                 # after a send, before the next poll
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20, 'eth_blockNumber': 10,
           'eth_gasPrice': 10, 'eth_estimateGas': 26}
CU_CAP = 98_000                # relay CU/day, hard cap in code (trial rule: <= 100,000)
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


def route_words(c, min_profit, max_gas_price, deadline):
    """Route = static tuple of 12 words: morpho, usdc, lt, v2pool, v2feeBps, mid, v3pool, mintSell, amount, minProfit,
    maxGasPrice, deadline."""
    return (aw(MORPHO) + aw(USDC) + aw(c['lt']) + aw(c['pair']) + word(V2_FEE_BPS) + aw(c['mid']) + aw(c['v3'])
            + word(1 if c['mint'] else 0) + word(c['amount']) + word(min_profit) + word(max_gas_price) + word(deadline))


def run_data(c, min_profit, max_gas_price, deadline):
    return SEL_RUN + route_words(c, min_profit, max_gas_price, deadline)


def probe_data(cands, deadline):
    body = ''.join(route_words(c, 1, MAX_FEE_WEI, deadline) for c in cands)
    return SEL_PROBE + word(32) + word(len(cands)) + body


CANDS = [{'name': f'{n}:{"mint" if m else "redeem"}:{s}', 'lt': lt, 'pair': pair, 'mid': mid, 'v3': v3, 'mint': m, 'amount': s * 10**6}
         for n, (lt, pair, mid, v3, sizes) in ROUTES.items() for m in (True, False) for s in sizes]


def signer():
    sys.path.append('/opt/farm/lib')
    import farmbot_signer
    return farmbot_signer


def owner():
    a = signer().my_address()
    a = a['address'] if isinstance(a, dict) else a
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def ctx():
    """(from, executor, state override list) for this mode."""
    if MODE == 'live':
        return owner(), EXEC, []
    return PAPER_OWNER, PAPER_EXEC, [{PAPER_EXEC: {'code': RUNTIME}}]


def probe(deadline):
    """One eth_call: the USDC gain (6 dp) of every candidate against the same state; 0 = it would revert."""
    frm, ex, ov = ctx()
    res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': probe_data(CANDS, deadline), 'gas': hex(30_000_000)}, 'latest'] + ov)
    h = res[2:]
    n = int(h[64:128], 16)
    if n != len(CANDS):
        raise RuntimeError('probe returned a wrong length')
    return [int(h[128 + 64 * i:192 + 64 * i], 16) for i in range(n)]


def hype_usd():
    sq = int(rpc('eth_call', [{'to': POOL_WHYPE, 'data': SEL_SLOT0}, 'latest'])[2:66], 16)
    return (sq / 2**96) ** 2 * 1e12        # USDT0 (6 dp) per WHYPE (18 dp)


def winner_block(lt, send_block, exec_addr):
    """Nearest block around our send where someone else minted or redeemed the token."""
    logs = rpc('eth_getLogs', [{'address': lt, 'fromBlock': hex(max(0, send_block - 120)),
                               'toBlock': hex(send_block + 5), 'topics': [[T_MINT, T_REDEEM]]}])
    best = None
    for x in logs:
        if '0x' + x['topics'][1][-40:].lower() == exec_addr.lower():
            continue
        b = int(x['blockNumber'], 16)
        if best is None or abs(b - send_block) < abs(best - send_block):
            best = b
    return best


def send_live(c, data, gas_limit, max_fee, priority, gain):
    reply = signer().send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', reply=reply)       # final: no retry
        return
    receipt = None
    for _ in range(25):
        time.sleep(1.0)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, result='unknown', gas_used=None, winner_block=None, candidate=c['name'])
        return
    b = int(receipt['blockNumber'], 16)
    used = int(receipt['gasUsed'], 16)
    status = int(receipt['status'], 16)
    try:
        other = winner_block(c['lt'], b, EXEC)
    except Exception:
        other = None
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16), send_block=b, winner_block=other,
        blocks_after_winner=(b - other if other is not None else None), simulated_gain_usdc=gain / 1e6,
        candidate=c['name'])


def evaluate(profits):
    """Take the best candidate; send (live) or log (paper) only if its gross exceeds this send's gas cap."""
    i = max(range(len(profits)), key=lambda k: profits[k])
    gain = profits[i]
    if gain == 0:
        return False
    c = CANDS[i]
    frm, ex, ov = ctx()
    deadline = int(time.time()) + 60
    base_fee = int(rpc('eth_gasPrice', []), 16)
    price = hype_usd() * HYPE_MARGIN
    try:
        est = int(rpc('eth_estimateGas', [{'from': frm, 'to': ex, 'data': run_data(c, 1, MAX_FEE_WEI, deadline)}, 'latest'] + ov), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        if MODE == 'live':
            log('opportunity_skip', candidate=c['name'], gain_usdc=gain / 1e6, reason='estimate_failed', error=str(e)[:160])
            return False
        est = int(GAS_LIMIT_FALLBACK / GAS_MARGIN)
    gas_limit = min(GAS_LIMIT_MAX, int(est * GAS_MARGIN))
    gross_usd = gain / 1e6
    gain_wei = int(gross_usd / price * 1e18)
    priority = int(gain_wei * BID_SHARE / gas_limit)
    max_fee = min(MAX_FEE_WEI, int(base_fee * 1.3) + priority)
    priority = min(priority, max_fee)
    gas_cap_usd = gas_limit * max_fee / 1e18 * price
    reason = None
    if max_fee < base_fee:
        reason = 'base_fee_above_fee_cap'
    elif gas_cap_usd >= SEND_CAP_USD:
        reason = 'gas_cap_over_usd_limit'
    elif gross_usd < gas_cap_usd * GAIN_OVER_CAP:
        reason = 'gross_under_1.5x_gas_cap'
    if reason:
        log('opportunity_skip', candidate=c['name'], gain_usdc=gross_usd, gas_cap_usd=gas_cap_usd, gas_limit=gas_limit,
            base_fee=base_fee, hype_usd=price, reason=reason)
        return False
    min_profit = max(1, int(gas_cap_usd * 1e6) + 1)          # the tx reverts unless the gain covers its own gas cap
    data = run_data(c, min_profit, max_fee, deadline)
    try:
        res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': data, 'gas': hex(gas_limit)}, 'latest'] + ov)   # the exact bytes
        gain = int(res[2:66], 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', candidate=c['name'], error=str(e)[:200])
        return False
    log('opportunity', candidate=c['name'], gain_usdc=gain / 1e6, min_profit_usdc=min_profit / 1e6, gas_cap_usd=gas_cap_usd,
        gas_limit=gas_limit, max_fee=max_fee, priority=priority, hype_usd=price, mode=MODE,
        profits={x['name']: p / 1e6 for x, p in zip(CANDS, profits) if p})
    if MODE == 'live':
        send_live(c, data, gas_limit, max_fee, priority, gain)
    else:
        log('paper_sim', result='success', candidate=c['name'], gain_usdc=gain / 1e6, gas_cap_usd=gas_cap_usd)
    return True


def main():
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, poll_s=POLL_S,
        candidates=[c['name'] for c in CANDS], cu_cap=CU_CAP)
    n = 0
    while True:
        try:
            profits = probe(int(time.time()) + 60)
            n += 1
            if n % 40 == 1:                                   # heartbeat about every 18 min
                log('poll', n=n, best_usdc=max(profits) / 1e6)
            if max(profits) >= MIN_GAIN_UNITS and evaluate(profits):
                time.sleep(COOLDOWN_S)
                continue
            time.sleep(POLL_S)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            nxt = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
            time.sleep(max(60, (nxt - now).total_seconds()))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            log('relay_error', error=str(e)[:180])
            time.sleep(POLL_S)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            time.sleep(POLL_S)


if __name__ == '__main__':
    main()
