#!/usr/bin/env python3
"""Trial: Fluid VaultT1 liquidations on Arbitrum through the TrialFluidTake executor.

Every POLL seconds one Multicall3 eth_call asks each vault what is liquidatable right now
(liquidate(1e30, 0, 0xdead, false) reverts FluidLiquidateResult(col, debt) by design) and reads
the WETH/USDC pool price. When a vault has debt to take, the executor call is simulated
(flash-swap the debt token out of a WETH pool, liquidate, turn the collateral into WETH, repay
the pool, keep the rest as native) and, live, sent. A lost attempt costs gas only (executor
NoProfit guard).
"""
import datetime
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
LANE = os.environ.get('RPC_LANE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
CHAIN = 'arbitrum'
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'
WETH = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'
USDC = '0xaf88d065e77c8cc2239327c5edb3a432268e5831'
USDT = '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9'
WBTC = '0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f'
ARB = '0x912ce59144191c1204e64559fe8253a0e49e6548'
WSTETH = '0x5979d7b546e38e414f7e9822514be443a4800529'
ZERO = '0x0000000000000000000000000000000000000000'
DEAD = '0x000000000000000000000000000000000000dead'
# UniV3 pools (factory 0x1f98431c..., getPool read on chain; scratch/trial-fluid-arb/pools.json)
P_WETH_USDC = '0xc6962004f452be9203591991d15f6b388e09e8d0'   # 0.05%, token0 WETH
P_WETH_USDT = '0x641c00a822e8b671738d32a431a4fb6074e5c79d'   # 0.05%, token0 WETH
P_WBTC_WETH = '0x2f5e87c9312fa29aed5c179e456625d79015299c'   # 0.05%
P_ARB_WETH = '0xc6f780497a95e246eb9449f5e4770916dcd6396a'    # 0.05%
P_WSTETH_WETH = '0x35218a1cbac5bbc3e57fd9bd38219d37571b3537'  # 0.01%
# Vaults are data (constantsView() read on chain; scratch/trial-fluid-arb/vaults.json).
# debt tokens have 6 decimals; max_repay keeps a take inside the pools' depth.
VAULTS = {
    'wbtc_usdc': {'vault': '0xe16a6f5359abb1f61ce71e25dd0932e3e00b00eb', 'debt': USDC, 'col': WBTC, 'native': False,
                  'pool1': P_WETH_USDC, 'pool2': P_WBTC_WETH, 'max_repay': 50_000 * 10**6},
    'wbtc_usdt': {'vault': '0x82b27fa821419f5689381b565a8b0786aa2548de', 'debt': USDT, 'col': WBTC, 'native': False,
                  'pool1': P_WETH_USDT, 'pool2': P_WBTC_WETH, 'max_repay': 50_000 * 10**6},
    'arb_usdc': {'vault': '0xdf16adaf80584b2723f3ba1eb7a601338ba18c4e', 'debt': USDC, 'col': ARB, 'native': False,
                 'pool1': P_WETH_USDC, 'pool2': P_ARB_WETH, 'max_repay': 10_000 * 10**6},
    'eth_usdc': {'vault': '0xeabbfca72f8a8bf14c4ac59e69ecb2eb69f0811c', 'debt': USDC, 'col': WETH, 'native': True,
                 'pool1': P_WETH_USDC, 'pool2': ZERO, 'max_repay': 50_000 * 10**6},
    'eth_usdt': {'vault': '0xbec491fef7b4f666b270f9d5e5c3f443cbf20991', 'debt': USDT, 'col': WETH, 'native': True,
                 'pool1': P_WETH_USDT, 'pool2': ZERO, 'max_repay': 50_000 * 10**6},
    'wsteth_usdc': {'vault': '0xa0f83fc5885cebc0420ce7c7b139adc80c4f4d91', 'debt': USDC, 'col': WSTETH, 'native': False,
                    'pool1': P_WETH_USDC, 'pool2': P_WSTETH_WETH, 'max_repay': 10_000 * 10**6},
}
T_LIQ = '0x80fd9cc6b1821f4a510e45ffce6852ea3404807b5d3d833ffa85664408afcb66'   # LogLiquidate(address,uint256,uint256,address)
SEL_TAKE = '0xb8e03f58'      # take((address,address,address,bool,address,address,address,uint256,uint256))
SEL_LIQ = '0x8433ea22'      # liquidate(uint256,uint256,address,bool)
SEL_RESULT = 'cc36aa44'      # FluidLiquidateResult(uint256,uint256)
SEL_SLOT0 = '0x3850c7bd'
SEL_TRYAGG = '0xbce38bd7'
PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'   # fork deployment; paper code override only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('missing paper executor runtime')
LOG = HERE / 'logs' / 'bot.jsonl'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
CU_FILE.parent.mkdir(exist_ok=True)

# ---- loss guard (trial rule: every send's gas cap < 1 USD) ----
POLL = 40                      # seconds between reads: 2,160 eth_calls/day
GAS_HARD_MAX = 3_000_000       # an estimate above this is not sent
GAS_MARGIN = 1.30              # gas limit = eth_estimateGas x 1.30 (Arbitrum: never a constant)
PAPER_GAS = 900_000            # paper only, when the node cannot estimate with a code override
SEND_CAP_USD = 0.95            # gasLimit x maxFeePerGas of one send must stay under this (< 1 USD)
ETH_MARGIN = 1.15              # ETH valued 15% above the pool price when sizing the cap
ETH_FALLBACK_USD = 4000.0      # used until the pool price has been read
ETH_MIN_USD = 1000.0           # an implausibly low read falls back to the high value
BID_SHARE = 0.40               # priority fee bid is at most 40% of simulated gross
MIN_DEBT = 1_000_000           # 1 USDC/USDT: below this the bonus cannot pay any send
CU_COST = {'eth_call': 26, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_gasPrice': 10, 'eth_estimateGas': 20}
CU_CAP = 90_000                # relay reads/day, hard cap in code (trial rule: <= 100,000)
_id = 0
_eth_usd = None
_cooldown = {}


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


def try_aggregate(calls):
    """Multicall3.tryAggregate(false, calls); calls = [(target, calldata hex)]. Returns [(ok, data hex)];
    a reverting call comes back as (False, revert data)."""
    starts, acc = [], 32 * len(calls)
    for _, data in calls:
        starts.append(acc)
        size = (len(data) - 2) // 2
        acc += 96 + ((size + 31) // 32) * 32
    enc = SEL_TRYAGG + word(0) + word(64) + word(len(calls)) + ''.join(word(x) for x in starts)
    for target, data in calls:
        size = (len(data) - 2) // 2
        enc += aw(target) + word(64) + word(size) + data[2:].ljust(((size + 31) // 32) * 64, '0')
    h = rpc('eth_call', [{'to': MULTICALL, 'data': enc}, 'latest'])[2:]
    if len(h) < 128:
        raise RuntimeError('short Multicall answer')
    n = int(h[64:128], 16)
    if n != len(calls):
        raise RuntimeError('Multicall length mismatch')
    out = []
    for i in range(n):
        start = 128 + int(h[128 + i * 64:192 + i * 64], 16) * 2
        ok = int(h[start:start + 64], 16) != 0
        off = int(h[start + 64:start + 128], 16)
        length = int(h[start + off * 2:start + off * 2 + 64], 16)
        out.append((ok, '0x' + h[start + off * 2 + 64:start + off * 2 + 64 + length * 2]))
    return out


PROBE = SEL_LIQ + word(10**30) + word(0) + aw(DEAD) + word(0)


def read_all():
    """One eth_call: what each vault would liquidate now, and the WETH/USDC pool price.
    Returns {name: (col, debt)}; a vault with nothing to take answers a FluidVaultError and maps to (0, 0)."""
    global _eth_usd
    names = list(VAULTS)
    res = try_aggregate([(VAULTS[k]['vault'], PROBE) for k in names] + [(P_WETH_USDC, SEL_SLOT0)])
    out = {}
    for k, (ok, data) in zip(names, res):
        d = data[2:]
        if not ok and d.startswith(SEL_RESULT) and len(d) >= 8 + 128:
            out[k] = (int(d[8:72], 16), int(d[72:136], 16))
        else:
            out[k] = (0, 0)
    ok, data = res[-1]
    if ok and len(data) >= 66:
        sqrt_p = int(data[2:66], 16)
        # token0 WETH (18 dec), token1 USDC (6 dec): USD per ETH = (sqrtP / 2^96)^2 x 1e12
        _eth_usd = (sqrt_p / 2**96) ** 2 * 1e12
    return out


def eth_ref_usd():
    """ETH price used to turn the fee cap into USD: pool read plus a margin, never a low guess."""
    if _eth_usd is None or _eth_usd < ETH_MIN_USD:
        return ETH_FALLBACK_USD
    return _eth_usd * ETH_MARGIN


def owner():
    sys.path.append('/opt/farm/lib')   # the live service does not put it on the path
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a['address'] if isinstance(a, dict) else a
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def calldata(k, amount, min_profit):
    """take(Take): one static tuple of 9 words."""
    v = VAULTS[k]
    return (SEL_TAKE + aw(v['vault']) + aw(v['debt']) + aw(v['col']) + word(1 if v['native'] else 0) + aw(WETH)
            + aw(v['pool1']) + aw(v['pool2']) + word(amount) + word(min_profit))


def sim(data, from_addr, exec_addr, code):
    tx = {'from': from_addr, 'to': exec_addr, 'data': data}
    params = [tx, 'latest'] + ([{exec_addr: {'code': code}}] if code else [])
    return int(rpc('eth_call', params)[2:66], 16)


def estimate_gas(data, from_addr, exec_addr, code):
    """Gas limit for this exact call from eth_estimateGas (on Arbitrum it includes the L1 data
    part). Live: no estimate = no send. Paper: the node may refuse a code override; then a
    nominal figure is logged."""
    tx = {'from': from_addr, 'to': exec_addr, 'data': data}
    if code is None:
        est = int(rpc('eth_estimateGas', [tx]), 16)
    else:
        try:
            est = int(rpc('eth_estimateGas', [tx, 'latest', {exec_addr: {'code': code}}]), 16)
        except ReadBudgetExceeded:
            raise
        except Exception:
            return PAPER_GAS, False
    return int(est * GAS_MARGIN), True


def winner_block(k, send_block, our_hash):
    lo = max(0, send_block - 400)
    hi = max(send_block, int(rpc('eth_blockNumber', []), 16))
    logs = rpc('eth_getLogs', [{'address': VAULTS[k]['vault'], 'fromBlock': hex(lo), 'toBlock': hex(hi), 'topics': [T_LIQ]}])
    ours = [int(x['blockNumber'], 16) for x in logs if x['transactionHash'].lower() == our_hash.lower()]
    if ours:
        return min(ours)
    return min((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(k, data, gas_limit, max_fee, priority, gross_usd):
    sys.path.append('/opt/farm/lib')
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=priority)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', vault=k, reply=reply)  # final: no retry
        return
    receipt = None
    for _ in range(30):  # arbitrum blocks are ~0.25 s; give up after 15 s
        time.sleep(0.5)
        receipt = rpc('eth_getTransactionReceipt', [h])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, vault=k, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    price = int(receipt['effectiveGasPrice'], 16)
    try:
        winner = winner_block(k, b, h)
    except Exception:
        winner = None
    log('send_result', hash=h, vault=k, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * price, winner_block=winner, send_block=b,
        blocks_after_winner=(b - winner if winner is not None else None), gross_usd=gross_usd)


def attempt(k, col, debt):
    now = time.time()
    if _cooldown.get(k, 0) > now:
        return
    _cooldown[k] = now + 20
    from_addr = owner() if MODE == 'live' else PAPER_OWNER
    exec_addr = EXEC if MODE == 'live' else PAPER_EXEC
    code = None if MODE == 'live' else RUNTIME
    amount = min(debt, VAULTS[k]['max_repay'])
    eth_usd = eth_ref_usd()
    try:
        profit = sim(calldata(k, amount, 1), from_addr, exec_addr, code)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        # normal while the oracle price gives no margin over the pool price (NoProfit) or someone took it
        _cooldown[k] = now + 120
        log('simulate_revert', vault=k, debt=amount, col=col, error=str(e)[:200])
        return
    gross_usd = profit / 1e18 * (_eth_usd or 0)
    try:
        gas_limit, estimated = estimate_gas(calldata(k, amount, 1), from_addr, exec_addr, code)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('opportunity_skip', vault=k, debt=amount, gross_usd=gross_usd, reason='estimate_gas_failed', error=str(e)[:200])
        return
    if gas_limit > GAS_HARD_MAX:
        log('opportunity_skip', vault=k, debt=amount, gross_usd=gross_usd, reason='gas_estimate_too_high', gas_limit=gas_limit)
        return
    base_fee = int(rpc('eth_gasPrice', []), 16)
    # hard fee cap: gas_limit x maxFeePerGas valued at eth_usd < SEND_CAP_USD
    fee_cap = int(SEND_CAP_USD / eth_usd * 1e18 / gas_limit)
    priority = int(profit * BID_SHARE / gas_limit)
    max_fee = min(fee_cap, base_fee * 2 + priority)
    priority = min(priority, max_fee)
    gas_cap_wei = gas_limit * max_fee
    gas_cap_usd = gas_cap_wei / 1e18 * eth_usd
    if max_fee < base_fee or gas_cap_usd >= 1.0 or profit <= gas_cap_wei:
        _cooldown[k] = now + 120
        log('opportunity_skip', vault=k, debt=amount, gross_usd=gross_usd, profit_wei=profit, gas_cap_usd=gas_cap_usd,
            base_fee=base_fee, eth_usd=eth_usd, gas_limit=gas_limit, reason='gross_not_above_gas_cap')
        return
    min_profit = max(1, gas_cap_wei)     # the executor reverts unless the take pays more than this send can cost
    data = calldata(k, amount, min_profit)
    try:
        profit = sim(data, from_addr, exec_addr, code)   # the exact bytes to send
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', vault=k, debt=amount, col=col, error=str(e)[:200])
        return
    log('opportunity', vault=k, debt=amount, col=col, gross_usd=gross_usd, profit_wei=profit, gas_cap_usd=gas_cap_usd,
        gas_limit=gas_limit, gas_estimated=estimated, max_fee=max_fee, priority=priority, eth_usd=eth_usd, mode=MODE)
    if MODE == 'live':
        send_live(k, data, gas_limit, max_fee, priority, gross_usd)
    else:
        log('paper_sim', vault=k, result='success', profit_wei=profit, gross_usd=gross_usd)


def main():
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, vaults=list(VAULTS), poll=POLL)
    n = 0
    while True:
        t0 = time.time()
        try:
            avail = read_all()
            live = {k: v for k, v in avail.items() if v[1] >= MIN_DEBT}
            if live or n % 15 == 0:      # a heartbeat row every 10 min, and every poll that sees debt to take
                log('scan', takeable={k: {'col': v[0], 'debt': v[1]} for k, v in live.items()}, eth_usd=_eth_usd)
            for k, (col, debt) in sorted(live.items(), key=lambda z: -z[1][1]):
                attempt(k, col, debt)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            time.sleep(600)
        except Exception as e:
            log('loop_error', error=str(e)[:250])
        n += 1
        time.sleep(max(1.0, POLL - (time.time() - t0)))


if __name__ == '__main__':
    main()
