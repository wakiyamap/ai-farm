#!/usr/bin/env python3
"""Trial: Ensemble leveraged vault shares (BULL, VOL) NAV versus their HyperSwap V3 pool on HyperEVM.

The vaults are ERC-4626 with instant deposit / redeem at a NAV read from HyperCore; the shares also trade on a
0.3 % pool. When the NAV has moved away from the pool by more than the fees, one transaction through the
TrialVaultArb executor flash-borrows USDC from Morpho Blue and either mints shares and sells them on the pool, or
buys shares on the pool and redeems them, repays, and pays the USDC gain to the bot wallet. The executor reverts
unless the gain is at least minProfit, so a lost attempt costs gas only.

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

# Route targets: all are call arguments of the executor (getters and traces: scratch/r93a5, lead 312)
MORPHO = '0x68e37de8d93d3496ae143f2e900490f6280c57cd'        # Morpho Blue (flash lender, no fee)
USDC = '0xb88339cb7199b77e23db6e890353e22632ba630f'          # HyperEVM USDC, 6 decimals (vault asset)
ROUTER = '0x1ebdfc75ffe3ba3de61e7138a3e8706ac841af9b'        # HyperSwap V3 SwapRouter
VAULTS = {                                                   # share token = vault; pool fee 3000 for both
    'BULL': '0x2d561b24e754b105bb0df34a3345aac1fe805210',    # pool 0x1ccdbc56a9235d59c1d001aa2724d31a10b38af4
    'VOL': '0xeb22ec1b402dcc4155b9d8d2e1db2f2d229162cc',     # pool 0x8e26ebc3ac380ff931c6f6731c9289514e62ec21
}
FEE = 3000
POOL_WHYPE = '0xbd19e19e4b70eb7f248695a42208bc1edbbfb57d'    # WHYPE/USDT0 0.05%, token0 WHYPE: HYPE price for the gas cap
SEL_RUN = '0x1cbe1813'       # cast sig run((address,address,address,address,uint24,bool,uint256,uint256,uint256,uint256))
SEL_PROBE = '0x93a3bc3e'     # cast sig probe((address,address,address,address,uint24,bool,uint256,uint256,uint256,uint256)[])
SEL_SLOT0 = '0x3850c7bd'     # cast sig slot0()
T_DEPOSIT = '0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'   # cast keccak Deposit(address,address,uint256,uint256)
T_WITHDRAW = '0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'  # cast keccak Withdraw(address,address,address,uint256,uint256)

PAPER_EXEC = '0x8f7a45ebde059392e46a46dcc14ab24681a961ea'    # fork deployment; paper code override only
PAPER_OWNER = '0x1111111111111111111111111111111111111111'   # the owner baked into that deployment (immutable)
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
GAS_LIMIT_FALLBACK = 1_200_000  # used only if eth_estimateGas fails (paper); live never sends without an estimate
GAS_MARGIN = 1.2               # proof: estimateGas 619,494 for BULL redeem 160
MAX_FEE_WEI = 2 * 10**9        # hard ceiling on maxFeePerGas: 1.9M x 2 gwei = 0.0038 HYPE
SEND_CAP_USD = 0.95            # the gas cap valued at the pool HYPE price x 1.15 must stay under this
HYPE_MARGIN = 1.15
BID_SHARE = 0.20               # priority fee bid is at most 20% of simulated gross
GAIN_OVER_CAP = 2.0            # send only if the simulated gain is at least twice this send's gas cap
MIN_GAIN_UNITS = 20_000        # 0.02 USDC: smaller probe gains are not evaluated at all (saves 62 CU per thin gap)
SIZES = [40, 80, 160, 320]     # USDC flash sizes (the flash incumbent uses 40 / 80 / 160)
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


def route_words(vault, mint_sell, amount, min_profit, max_gas_price, deadline):
    """Route = static tuple of 10 words: morpho, asset, vault, router, fee, mintSell, amount, minProfit, maxGasPrice, deadline."""
    return (aw(MORPHO) + aw(USDC) + aw(vault) + aw(ROUTER) + word(FEE) + word(1 if mint_sell else 0)
            + word(amount) + word(min_profit) + word(max_gas_price) + word(deadline))


def run_data(c, min_profit, max_gas_price, deadline):
    return SEL_RUN + route_words(c['vault'], c['mint'], c['amount'], min_profit, max_gas_price, deadline)


def probe_data(cands, deadline):
    body = ''.join(route_words(c['vault'], c['mint'], c['amount'], 1, MAX_FEE_WEI, deadline) for c in cands)
    return SEL_PROBE + word(32) + word(len(cands)) + body


CANDS = [{'name': f'{n}:{"mint" if m else "redeem"}:{s}', 'vault': v, 'mint': m, 'amount': s * 10**6}
         for n, v in VAULTS.items() for m in (True, False) for s in SIZES]


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


def winner_block(vault, send_block, exec_addr):
    """Nearest block around our send where someone else deposited into or redeemed from the vault."""
    logs = rpc('eth_getLogs', [{'address': vault, 'fromBlock': hex(max(0, send_block - 120)),
                               'toBlock': hex(send_block + 5), 'topics': [[T_DEPOSIT, T_WITHDRAW]]}])
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
        other = winner_block(c['vault'], b, EXEC)
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
        reason = 'gross_under_2x_gas_cap'
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
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, poll_s=POLL_S, sizes=SIZES,
        vaults=VAULTS, cu_cap=CU_CAP)
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
