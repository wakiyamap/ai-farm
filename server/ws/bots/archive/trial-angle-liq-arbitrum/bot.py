#!/usr/bin/env python3
"""trial: Angle Borrow (EURA-debt vaults) liquidations on Arbitrum. VaultManager.liquidate is open to anyone: the
caller's EURA is burned and the vault's collateral is paid at the oracle price divided by a discount (up to 10 pct).
EURA has almost no DEX liquidity on Arbitrum; the takers get it by buying stEUR (Angle savings, ERC-4626 over EURA)
on its Camelot (Algebra) stEUR/USDC pool and redeeming it. One Morpho-flash-funded transaction through the StepArb
executor does: USDC -> stEUR (Camelot) -> redeem to EURA -> liquidate -> collateral -> USDC (Uniswap V3), sends any
EURA left back through stEUR to USDC, repays, and keeps the rest in USDC.
Timer bot: every POLL seconds one Multicall3 eth_call per VaultManager reads checkLiquidation of every vault with
debt; a liquidatable vault is then priced with one probe() eth_call."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'arbitrum'

# Addresses: from the incumbents' traced takes and the Treasury's vaultManagerList, each checked with a getter
# (README, "Addresses"; scratch/trial-angle-liq-arbitrum/setup.sh and discover.py).
MORPHO = '0x6c247b1F6182318877311737BaC0844bAa518F5e'    # Morpho Blue, flashLoan(token, assets, data), no fee
USDC = '0xaf88d065e77c8cC2239327C5EDb3A432268e5831'
USDCE = '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'
WETH = '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1'
WBTC = '0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f'
EURA = '0xFA5Ed56A203466CbBC2430a43c66b9D8723528E7'     # Treasury 0x0d710512.stablecoin()
STEUR = '0x004626A008B1aCdC4c74ab51644093b155e59A23'    # asset() = EURA
CAMELOT = '0x1F721E2E82F6676FCE4eA07A5958cF098D339e18'  # Camelot Algebra SwapRouter, factory() = the stEUR/USDC pool's factory()
UNIV3 = '0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45'    # Uniswap V3 SwapRouter02 (factory() = 0x1F98431c...)
MULTICALL3 = '0xcA11bde05977b3631167028862bE2a173976CA11'
# VaultManagers of the EURA Treasury 0x0d710512e100c171139d2cf5708f22c680eccf52 (vaultManagerList 0..4; the two
# staked-Curve-LP managers are left out: one vault each and no one-swap exit to USDC).
# key -> (VaultManager, collateral, Uniswap V3 fee tier of the collateral/USDC pool)
VMS = {'wbtc': ('0xF664118E79C0B34f1Ed20e6606a0068d213839b9', WBTC, 500),
       'weth': ('0xe9f183FC656656f1F17af1F2b0dF79b8fF9ad8eD', WETH, 500),
       'usdce': ('0x04437E94aF860AFBb0429A7D36B9C00a5a5173B9', USDCE, 100)}

# Selectors, all from `cast sig` (scratch/trial-angle-liq-arbitrum/setup.sh).
SEL_TAKE = '0x13b75307'       # take(address,address,uint256,(address,address,address,uint256,uint256,bytes)[],address[],uint256,bool)
SEL_PROBE = '0x8ad8bbaf'      # probe(bytes[])
SEL_ALGEBRA = '0xbc651188'    # exactInputSingle((address,address,address,uint256,uint256,uint256,uint160))
SEL_V3 = '0x04e45aaf'         # exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))
SEL_REDEEM = '0xba087652'     # redeem(uint256,address,address)
SEL_DEPOSIT = '0x6e553f65'    # deposit(uint256,address)
SEL_LIQUIDATE = '0xfc29b021'  # liquidate(uint256[],uint256[],address,address)
SEL_AGG3 = '0x82ad56cb'       # aggregate3((address,bool,bytes)[])
SEL_VAULTDATA = '0x7aacfffa'  # vaultData(uint256) -> (collateralAmount, normalizedDebt)
SEL_CHECK = '0x307439af'      # checkLiquidation(uint256,address) -> (maxStablecoinAmountToRepay, maxCollateralAmountGiven, thresholdRepayAmount, discount, currentDebt)
SEL_COUNT = '0x3c2e941b'      # vaultIDCount()
TOPIC_LIQUIDATED = '0x965a177723c641ee49150b583a0b9ad4730bb20d3474e00ae5a65e777c00d67b'   # LiquidatedVaults(uint256[])

PAPER_EXEC = '0x00000000000000000000000000000000000f11a8'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

CLEAR = (EURA, STEUR, WBTC, WETH, USDCE)
# USDC flash per EURA of the vault's maximum repay (stEUR costs about 1.10-1.16 USDC per EURA of redeem value)
RATIOS_MILLI = (1080, 1110, 1140, 1170, 1210, 1270, 1350)
PARTS = (4, 2)                    # for vaults without a threshold: also 1/4 and 1/2 of the maximum
MIN_REPAY_EURA_WEI = 10**18       # vaults whose maximum repay is under 1 EURA are dust: skipped
MAX_FLASH_USDC = 20_000 * 10**6   # the stEUR pool cannot fill more; a larger vault is taken in parts
MIN_INTEREST_USDC = 50_000        # 0.05 USDC: below this a take cannot cover its gas
POLL = 300                        # seconds between scans
ACTIVE_REFRESH = 6 * 3600         # seconds between rebuilds of the list of vaults with debt
FOLLOW_UPS = (10, 30)             # seconds after a look that left a gain standing below the send line
TIP_WEI = 0                       # Arbitrum orders by arrival: no priority fee, never raised
MAX_FEE_CAP_WEI = 5 * 10**8       # 0.5 gwei: never sign above this
GAS_LIMIT_MAX = 3_000_000
ETH_REF_USD = 4000.0              # conservative on purpose (about 1,800 USD on 2026-11-21): overstates gas in USD
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


# ---- ABI encoding (static words and the dynamic shapes take(), probe() and aggregate3() need) ----
def w(n):
    return format(n, '064x')


def a(addr):
    return addr.lower().removeprefix('0x').zfill(64)


def step(target, token_in, spender, data, offset, amount=0):
    return {'target': target, 'tokenIn': token_in or '0x' + '00' * 20,
            'spender': spender or '0x' + '00' * 20, 'amount': amount, 'offset': offset, 'data': data}


def algebra_swap(token_in, token_out, to):
    # exactInputSingle((tokenIn, tokenOut, recipient, deadline, amountIn, amountOutMinimum, limitSqrtPrice))
    return step(CAMELOT, token_in, CAMELOT,
                SEL_ALGEBRA + a(token_in) + a(token_out) + a(to) + w(2**40) + w(0) + w(0) + w(0), 4 + 4 * 32)


def route_steps(vm_key, vault_id, to):
    vm, coll, fee = VMS[vm_key]
    return [
        algebra_swap(USDC, STEUR, to),                                                   # the whole USDC flash -> stEUR
        step(STEUR, STEUR, None, SEL_REDEEM + w(0) + a(to) + a(to), 4),                  # redeem(shares, receiver, owner) -> EURA
        # liquidate([vaultID], [amount], from, to): amount = the whole EURA balance (the manager caps it at the
        # vault's maximum); collateral to the executor
        step(vm, EURA, vm, SEL_LIQUIDATE + w(0x80) + w(0xc0) + a(to) + a(to) + w(1) + w(vault_id) + w(1) + w(0), 4 + 7 * 32),
        # exactInputSingle((tokenIn, tokenOut, fee, recipient, amountIn, amountOutMinimum, sqrtPriceLimitX96)): collateral -> USDC
        step(UNIV3, coll, UNIV3, SEL_V3 + a(coll) + a(USDC) + w(fee) + a(to) + w(0) + w(0) + w(0), 4 + 4 * 32),
        step(STEUR, EURA, STEUR, SEL_DEPOSIT + w(0) + a(to), 4),                         # EURA left over -> stEUR (skipped at 0)
        algebra_swap(STEUR, USDC, to),                                                   # stEUR left over -> USDC (skipped at 0)
    ]


def enc_step(s):
    data = bytes.fromhex(s['data'].removeprefix('0x'))
    pad = (-len(data)) % 32
    return (a(s['target']) + a(s['tokenIn']) + a(s['spender']) + w(s['amount']) + w(s['offset'])
            + w(6 * 32) + w(len(data)) + data.hex() + '00' * pad)


def take_calldata(vm_key, vault_id, amount, min_profit, executor):
    steps = [enc_step(s) for s in route_steps(vm_key, vault_id, executor)]
    offs, pos = [], 32 * len(steps)
    for s in steps:
        offs.append(pos)
        pos += len(s) // 2
    steps_blob = w(len(steps)) + ''.join(w(o) for o in offs) + ''.join(steps)
    clear_blob = w(len(CLEAR)) + ''.join(a(t) for t in CLEAR)
    head = 7 * 32
    # unwrap = false: the gain is sent to the owner (the bot wallet) as USDC
    return (SEL_TAKE + a(MORPHO) + a(USDC) + w(amount) + w(head) + w(head + len(steps_blob) // 2)
            + w(min_profit) + w(0) + steps_blob + clear_blob)


def bytes_array(calls):
    blobs = []
    for c in calls:
        raw = c.removeprefix('0x')
        blobs.append(w(len(raw) // 2) + raw + '00' * ((-(len(raw) // 2)) % 32))
    offs, pos = [], 32 * len(blobs)
    for b in blobs:
        offs.append(pos)
        pos += len(b) // 2
    return w(len(blobs)) + ''.join(w(o) for o in offs) + ''.join(blobs)


def probe_calldata(calls):
    """probe(bytes[]) with one take() calldata per candidate."""
    return SEL_PROBE + w(32) + bytes_array(calls)


def aggregate3(calls, block='latest'):
    """Multicall3.aggregate3 with allowFailure = true; returns [(ok, hex without 0x)] in ONE eth_call."""
    blobs = []
    for to, data in calls:
        raw = data.removeprefix('0x')
        blobs.append(a(to) + w(1) + w(96) + w(len(raw) // 2) + raw + '00' * ((-(len(raw) // 2)) % 32))
    offs, pos = [], 32 * len(blobs)
    for b in blobs:
        offs.append(pos)
        pos += len(b) // 2
    data = SEL_AGG3 + w(32) + w(len(blobs)) + ''.join(w(o) for o in offs) + ''.join(blobs)
    res = bytes.fromhex(rpc('eth_call', [{'to': MULTICALL3, 'data': data}, block])[2:])
    n = int.from_bytes(res[32:64], 'big')
    out = []
    for i in range(n):
        o = 64 + int.from_bytes(res[64 + 32 * i:96 + 32 * i], 'big')
        ok = int.from_bytes(res[o:o + 32], 'big')
        ro = o + int.from_bytes(res[o + 32:o + 64], 'big')
        ln = int.from_bytes(res[ro:ro + 32], 'big')
        out.append((bool(ok), res[ro + 32:ro + 32 + ln].hex()))
    return out


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


def active_vaults(block='latest'):
    """vm_key -> ids of the vaults with debt (normalizedDebt > 0). One vaultIDCount call and one Multicall3 call
    per 400 vault ids."""
    out = {}
    for key, (vm, _, _) in VMS.items():
        count = int(rpc('eth_call', [{'to': vm, 'data': SEL_COUNT}, block]), 16)
        ids = list(range(1, count + 1))
        act = []
        for k in range(0, len(ids), 400):
            chunk = ids[k:k + 400]
            for i, (ok, h) in zip(chunk, aggregate3([(vm, SEL_VAULTDATA + w(i)) for i in chunk], block)):
                if ok and len(h) >= 128 and int(h[64:128], 16) > 0:
                    act.append(i)
        out[key] = act
    return out


def liquidatable(active, block='latest'):
    """[(vm_key, vault id, max repay EURA wei, max collateral, threshold, discount 1e9, debt)] of the vaults that
    checkLiquidation prices now (a healthy vault reverts HealthyVault() 0x57fa6d84), largest first."""
    found = []
    for key, ids in active.items():
        vm = VMS[key][0]
        for k in range(0, len(ids), 300):
            chunk = ids[k:k + 300]
            calls = [(vm, SEL_CHECK + w(i) + a(executor())) for i in chunk]
            for i, (ok, h) in zip(chunk, aggregate3(calls, block)):
                if ok and len(h) >= 64 * 5:
                    words = [int(h[64 * j:64 * j + 64], 16) for j in range(5)]
                    if words[0] >= MIN_REPAY_EURA_WEI:
                        found.append((key, i, *words))
    return sorted(found, key=lambda x: -x[2])


def vault_candidates(key, vault_id, max_repay, threshold):
    """(vm_key, vault id, USDC flash) candidates for one vault."""
    base = max_repay // 10**12                       # EURA wei -> USDC units at 1:1
    sizes = [base * r // 1000 for r in RATIOS_MILLI]
    if threshold == 0:                               # a partial repay is allowed
        sizes += [base * 1140 // 1000 // p for p in PARTS]
    return [(key, vault_id, min(s, MAX_FLASH_USDC)) for s in sorted(set(sizes)) if s > 0]


def call_params(data, gas_limit=None, block='latest'):
    ex = executor()
    tx = {'from': owner() if MODE == 'live' else PAPER_OWNER, 'to': ex, 'data': data}
    if gas_limit is not None:
        tx['gas'] = hex(gas_limit)
    params = [tx, block]
    if MODE == 'paper':
        params.append({ex: {'code': RUNTIME_FILE.read_text().strip()}})
    return params


def probe(cands, block='latest'):
    """Gains (USDC units) of every candidate in ONE eth_call; 0 = that take would revert."""
    ex = executor()
    data = probe_calldata([take_calldata(k, i, amt, 1, ex) for k, i, amt in cands])
    res = rpc('eth_call', call_params(data, None, block))
    words = [int(res[2 + i:2 + i + 64], 16) for i in range(0, len(res) - 2, 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(cands):
        raise RuntimeError('probe: unexpected return length')
    return gains


def gain_of(cand, min_profit=1, gas_limit=None, block='latest'):
    """Gain in USDC units of take() as an eth_call; 0 when it reverts (NoProfit or a failed step)."""
    k, i, amt = cand
    ans = rpc('eth_call', call_params(take_calldata(k, i, amt, min_profit, executor()), gas_limit, block), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def fees():
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    return base_fee, base_fee + base_fee // 4 + TIP_WEI


def last_take_block(vm_key, block):
    """Block of the newest LiquidatedVaults on the manager near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': VMS[vm_key][0], 'fromBlock': hex(block - 400), 'toBlock': hex(block + 20),
                                'topics': [TOPIC_LIQUIDATED]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(cand, gross, cap_usdc, max_fee, gas_limit):
    import farmbot_signer
    k, i, amt = cand
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(k, i, amt, cap_usdc, EXEC), 0, gas_limit,
                                max_fee, max_priority_fee_per_gas=TIP_WEI)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', reply=reply)
        return
    receipt = None
    for _ in range(20):
        time.sleep(1.5)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=tx_hash, result='unknown', vm=k, vault=i, flash_usdc=amt, expected_gross_usdc=gross,
            cap_usdc=cap_usdc, gas_limit=gas_limit, max_fee_wei=max_fee, gas_used=None, winner_block=None)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        winner = block if status else last_take_block(k, block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', hash=tx_hash, result='won' if status else 'lost', vm=k, vault=i, flash_usdc=amt,
        gas_used=used, gas_limit=gas_limit, max_fee_wei=max_fee, cap_usdc=cap_usdc, gas_cost_wei=cost,
        expected_gross_usdc=gross, send_block=block, winner_block=winner, tx_index=int(receipt['transactionIndex'], 16))


def try_vault(trigger, key, vault_id, max_repay, threshold, discount):
    """Price one liquidatable vault and take it if the gain is above the send's gas cap. True = a gain was seen."""
    cands = vault_candidates(key, vault_id, max_repay, threshold)
    gains = probe(cands)
    gross = max(gains)
    cand = cands[gains.index(gross)]
    if gross < MIN_INTEREST_USDC:
        log('check', trigger=trigger, result='no_gain', vm=key, vault=vault_id, max_repay_eura_wei=max_repay,
            discount_1e9=discount, best_usdc=gross)
        return False
    base_fee, max_fee = fees()
    if max_fee > MAX_FEE_CAP_WEI:
        log('opportunity_skip', trigger=trigger, reason='fee_cap', vm=key, vault=vault_id, gross_usdc=gross, base_fee=base_fee)
        return True
    data = take_calldata(key, vault_id, cand[2], 1, executor())
    try:
        estimate = int(rpc('eth_estimateGas', call_params(data)), 16)       # Arbitrum: always from eth_estimateGas
    except Exception as e:
        log('simulate_revert', trigger=trigger, step='estimate', vm=key, vault=vault_id, gross_usdc=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 12 // 10
    cap_wei = gas_limit * max_fee                                            # the most this send can cost
    cap_usd = cap_wei / 1e18 * ETH_REF_USD
    cap_usdc = int(cap_usd * 1e6) + 1                                        # the same cap in USDC units (minProfit)
    log('opportunity', trigger=trigger, vm=key, vault=vault_id, flash_usdc=cand[2], gross_usdc=gross, cap_usdc=cap_usdc,
        cap_wei=cap_wei, base_fee=base_fee, max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit,
        max_repay_eura_wei=max_repay, discount_1e9=discount)
    if gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='gas_limit_or_usd_cap', vm=key, vault=vault_id, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross <= cap_usdc:                                                    # send only when expected gross > this send's gas cap
        log('opportunity_skip', reason='gross_not_above_gas_cap', vm=key, vault=vault_id, gross_usdc=gross, cap_usdc=cap_usdc)
        return True
    checked, err = gain_of(cand, cap_usdc, gas_limit)                        # the exact call that would be signed
    if checked <= cap_usdc:
        log('simulate_revert', step='guard', vm=key, vault=vault_id, gross_usdc=gross, cap_usdc=cap_usdc, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', trigger=trigger, vm=key, vault=vault_id, flash_usdc=cand[2], gross_usdc=checked,
            cap_usdc=cap_usdc, gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=TIP_WEI)
    else:
        send_live(cand, checked, cap_usdc, max_fee, gas_limit)
    return True                                                              # look again: part of the vault may be left


def check(active, trigger='manual'):
    """One scan. Returns True when a gain was seen (taken or not): the caller schedules follow-up looks."""
    found = liquidatable(active)
    if not found:
        log('check', trigger=trigger, result='none_liquidatable', vaults=sum(len(v) for v in active.values()))
        return False
    seen = False
    for key, vault_id, max_repay, _max_coll, threshold, discount, _debt in found[:3]:   # the three largest
        seen = try_vault(trigger, key, vault_id, max_repay, threshold, discount) or seen
    return seen


def main():
    """Timer loop. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), managers={k: v[0] for k, v in VMS.items()},
        poll_seconds=POLL, follow_ups=list(FOLLOW_UPS))
    follow_ups = []
    next_poll = 0
    active, active_at = None, 0
    while True:
        try:
            now = time.time()
            if active is None or now - active_at > ACTIVE_REFRESH:
                active = active_vaults()
                active_at = now
                log('active', vaults={k: len(v) for k, v in active.items()})
            if follow_ups and now >= follow_ups[0]:
                follow_ups = follow_ups[1:]
                check(active, 'follow_up')
            elif now >= next_poll:
                next_poll = now + POLL
                seen = check(active, 'timer')
                # follow-ups only live (after a send, part of the vault may be left); in paper a vault nobody takes
                # would otherwise triple the read cost
                follow_ups = [time.time() + d for d in FOLLOW_UPS] if (seen and MODE == 'live') else []
            else:
                time.sleep(max(0.5, min([next_poll] + follow_ups[:1]) - now))
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            follow_ups = []
            now = datetime.datetime.now(datetime.timezone.utc)
            time.sleep(86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 5)   # to 00:00 UTC
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            next_poll = time.time() + POLL
            time.sleep(5)


if __name__ == '__main__':
    main()
