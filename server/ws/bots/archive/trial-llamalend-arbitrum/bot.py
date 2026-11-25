#!/usr/bin/env python3
"""One-market, flash-funded Curve LlamaLend liquidation trial on Arbitrum."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ['RPC_RELAY_URL'].rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'arbitrum'
CTRL = '0xb9adddcf4e01c2f64f8f2cd9a050dc35585ea053'  # explorer verified controller, WBTC collateral
VAULT = '0xba12222222228d8ba445958a75a0704d566bf2c8'  # explorer verified Balancer V2 Vault
ROUTER = '0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45'  # explorer verified Uni SwapRouter02
CURVE = '0x845c8bc94610807fcbab5dd2bc7ac9dabaff3c55'  # explorer verified tricrypto
WBTC = '0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f'  # controller.collateral_token()
CRVUSD = '0x498bf2b1e120fed3ad3d42ea2165e9b73f99c1e5'  # controller.borrowed_token()
ARB = '0x912ce59144191c1204e64559fe8253a0e49e6548'  # Curve coins(1)
WETH = '0x82af49447d8a07e3bd95bd0d56f35241523fbab1'  # Balancer Vault WETH
PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'  # owner of the fork-proof deployment (proof.py); paper only
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_ARBITRUM or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip() if MODE == 'paper' else None

SEL_USERS = '0x007c98ab'  # cast sig users_to_liquidate()
SEL_TAKE = '0x1814cc15'  # cast sig take((address,address,address,address,address,address,address,address,address,bytes,bytes,bytes,uint256,uint256))
T_LIQ = '0x642dd4d37ddd32036b9797cec464c0045dd2118c549066ae6b0f88e32240c2d0'  # cast keccak Liquidate(address,address,uint256,uint256,uint256)
T_WITHDRAW = '0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65'  # cast keccak Withdrawal(address,uint256)
MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'  # Multicall3, getChainId() answers 42161
SEL_AGG3 = '0x82ad56cb'  # cast sig aggregate3((address,bool,bytes)[])
SEL_NLOANS = '0x6cce39be'  # cast sig n_loans()
SEL_LOANS = '0xe1ec3c68'  # cast sig loans(uint256)
SEL_HEALTH = '0x8908ea82'  # cast sig health(address,bool)
MAX_LOANS = 400
LOANS_REFRESH_SECONDS = 1800
NEAR_HEALTH = 500_000_000_000_000  # 0.05% (1e18 = 100%): a borrower this close to zero switches to the fast poll
FAST_SECONDS = 3
FAST_POLLS_PER_DAY = 1400  # 70 min of fast polling per UTC day = 36,400 CU
LOANS = [1_700_000_000_000_000, 3_000_000_000_000_000, 10_000_000_000_000_000, 50_000_000_000_000_000]
POLL_SECONDS = 75
FAIL_RETRY_SECONDS = 600
SEND_RETRY_SECONDS = 300
CU_CAP = 90_000
ETH_REF_USD = 4_000.0  # conservative USD conversion for the one-dollar trial cap
MAX_SEND_USD = 0.80
MAX_BID_SHARE = 0.50  # upper bound on maxFeePerGas x gasLimit relative to simulated gross
CU_COST = {'eth_call': 26, 'eth_estimateGas': 26, 'eth_gasPrice': 20,
           'eth_getTransactionReceipt': 20, 'eth_getLogs': 75}

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

class BudgetError(Exception):
    pass

def log(ev, **fields):
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': round(time.time(), 3), 'ev': ev, **fields}, separators=(',', ':')) + '\n')

def rpc(method, params):
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(STATE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    cost = CU_COST.get(method, 26)
    if budget['cu'] + cost > CU_CAP:
        raise BudgetError(f'{CU_CAP} CU/day cap')
    budget['cu'] += cost
    STATE.write_text(json.dumps(budget))
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    request = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as resp:
        result = json.load(resp)
    if 'error' in result:
        raise RuntimeError(f'{method}: {str(result["error"])[:200]}')
    return result['result']

def word(n):
    return format(n, '064x')

def aw(addr):
    return addr.lower().removeprefix('0x').zfill(64)

def path(a, b):
    return bytes.fromhex(a[2:] + '0001f4' + b[2:])  # verified UniV3 0.05% pools

def tail(blob):
    return word(len(blob)) + blob.hex().ljust(((len(blob) + 31) // 32) * 64, '0')

def calldata(user, loan, min_profit):
    paths = [path(WETH, ARB), path(WBTC, WETH), path(ARB, WETH)]
    head = [aw(a) for a in (VAULT, CTRL, user, WBTC, CRVUSD, ARB, WETH, CURVE, ROUTER)]
    offset = 14 * 32
    tails = []
    for p in paths:
        head.append(word(offset))
        encoded = tail(p)
        tails.append(encoded)
        offset += len(encoded) // 2
    head.extend((word(loan), word(min_profit)))
    return SEL_TAKE + word(32) + ''.join(head) + ''.join(tails)

def owner():
    import farmbot_signer
    result = farmbot_signer.my_address()
    address = result['address'] if isinstance(result, dict) else result
    if not isinstance(address, str) or len(address) != 42:
        raise RuntimeError('signer my_address returned no address')
    return address

def tx(user, loan, min_profit):
    return {'from': owner() if MODE == 'live' else PAPER_OWNER,
            'to': EXEC if MODE == 'live' else PAPER_EXEC,
            'data': calldata(user, loan, min_profit)}

def override():
    return {PAPER_EXEC: {'code': RUNTIME}} if MODE == 'paper' else None

def simulate(user, loan, min_profit):
    params = [tx(user, loan, min_profit), 'latest']
    if MODE == 'paper':
        params.append(override())
    return int(rpc('eth_call', params), 16)

def estimate(user, loan):
    params = [tx(user, loan, 1), 'latest']
    if MODE == 'paper':
        params.append(override())
    return int(rpc('eth_estimateGas', params), 16)

def users():
    raw = bytes.fromhex(rpc('eth_call', [{'to': CTRL, 'data': SEL_USERS}, 'latest'])[2:])
    if len(raw) < 64:
        raise RuntimeError('short users_to_liquidate return')
    off = int.from_bytes(raw[:32], 'big')
    n = int.from_bytes(raw[off:off+32], 'big')
    if n > 200 or len(raw) < off + 32 + n * 160:
        raise RuntimeError(f'bad users_to_liquidate count {n}')
    found = []
    for i in range(n):
        start = off + 32 + i * 160
        user = '0x' + raw[start+12:start+32].hex()
        health = int.from_bytes(raw[start+128:start+160], 'big', signed=True)
        if health < 0:
            found.append((user, health))
    return found

def aggregate3(calls):
    """One eth_call for many reads: Multicall3.aggregate3 with allowFailure. calls = [(target, calldata hex)]."""
    n = len(calls)
    offs, tuples, pos = [], [], n * 32
    for target, data in calls:
        raw = bytes.fromhex(data[2:])
        enc = aw(target) + word(1) + word(96) + tail(raw)
        offs.append(word(pos))
        tuples.append(enc)
        pos += len(enc) // 2
    out = rpc('eth_call', [{'to': MULTICALL, 'data': SEL_AGG3 + word(32) + word(n) + ''.join(offs) + ''.join(tuples)}, 'latest'])
    raw = bytes.fromhex(out[2:])
    if len(raw) < 64 or int.from_bytes(raw[32:64], 'big') != n:
        raise RuntimeError('bad aggregate3 return')
    res = []
    for i in range(n):
        base = 64 + int.from_bytes(raw[64 + 32 * i:96 + 32 * i], 'big')
        ok = int.from_bytes(raw[base:base + 32], 'big') == 1
        doff = base + int.from_bytes(raw[base + 32:base + 64], 'big')
        dlen = int.from_bytes(raw[doff:doff + 32], 'big')
        res.append(raw[doff + 32:doff + 32 + dlen] if ok else None)
    return res

def borrowers():
    """Every open loan of the controller: n_loans() then loans(i) in one Multicall."""
    n = int(rpc('eth_call', [{'to': CTRL, 'data': SEL_NLOANS}, 'latest']), 16)
    if n == 0:
        return []
    if n > MAX_LOANS:
        raise RuntimeError(f'n_loans {n} above {MAX_LOANS}')
    out = aggregate3([(CTRL, SEL_LOANS + word(i)) for i in range(n)])
    return ['0x' + r[12:32].hex() for r in out if r is not None and len(r) >= 32]

def healths(addrs):
    """health(user, true) per borrower: the value liquidate() itself tests ('Not enough rekt' unless < 0)."""
    out = aggregate3([(CTRL, SEL_HEALTH + aw(a) + word(1)) for a in addrs])
    return [(a, int.from_bytes(r[:32], 'big', signed=True)) for a, r in zip(addrs, out) if r is not None and len(r) >= 32]

def winner_block(block):
    logs = rpc('eth_getLogs', [{'address': CTRL, 'fromBlock': hex(max(0, block - 100)),
                               'toBlock': hex(block), 'topics': [T_LIQ]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)

def send_live(user, loan, gross, cap, gas_limit, max_fee, min_profit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, calldata(user, loan, min_profit), 0,
                                gas_limit, max_fee, max_priority_fee_per_gas=0)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', user=user, reply=reply)
        return
    receipt = None
    for _ in range(30):
        time.sleep(1)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    if not receipt:
        log('send_result', hash=tx_hash, result='unknown', user=user, gas_used=None,
            winner_block=None, gross_wei=gross, cap_wei=cap)
        return
    used = int(receipt['gasUsed'], 16)
    gas_cost = used * int(receipt['effectiveGasPrice'], 16)
    block = int(receipt['blockNumber'], 16)
    success = int(receipt['status'], 16) == 1
    paid = 0
    if success:
        for item in receipt.get('logs', []):
            if item['address'].lower() == WETH.lower() and item['topics'][0].lower() == T_WITHDRAW:
                if len(item['topics']) > 1 and item['topics'][1][-40:].lower() == EXEC[-40:].lower():
                    paid += int(item['data'], 16)
    try:
        winner = winner_block(block)
    except Exception as exc:
        log('winner_lookup_error', hash=tx_hash, error=str(exc)[:160])
        winner = None
    log('send_result', hash=tx_hash, result='won' if success else 'lost', user=user,
        gas_used=used, gas_cost_wei=gas_cost, paid_wei=paid, net_wei=paid-gas_cost,
        gross_wei=gross, cap_wei=cap, block=block, winner_block=winner,
        blocks_after_winner=block-winner if winner is not None else None)

def check_user(user, health):
    best = None
    for loan in LOANS:
        try:
            gross = simulate(user, loan, 1)
        except Exception as exc:
            log('simulate_revert', user=user, loan_wei=loan, error=str(exc)[:180])
            continue
        if best is None or gross > best[1]:
            best = (loan, gross)
    if best is None:
        return
    loan, gross = best
    log('opportunity', user=user, health=health, loan_wei=loan, gross_wei=gross)
    try:
        gas_limit = (estimate(user, loan) * 12 + 9) // 10
        gas_price = int(rpc('eth_gasPrice', []), 16)
    except Exception as exc:
        log('estimate_error', user=user, error=str(exc)[:180])
        return
    max_fee = min((gas_price * 11 + 9) // 10,
                  int(MAX_SEND_USD / ETH_REF_USD * 1e18) // gas_limit,
                  int(gross * MAX_BID_SHARE) // gas_limit)
    cap = max_fee * gas_limit
    if max_fee < gas_price or cap <= 0 or gross <= cap:
        log('opportunity_skip', user=user, reason='gas_cap_or_bid', gas_price=gas_price,
            max_fee=max_fee, gross_wei=gross, cap_wei=cap)
        return
    min_profit = cap + 1
    try:
        final_gross = simulate(user, loan, min_profit)
    except Exception as exc:
        log('opportunity_skip', user=user, reason='final_sim_revert', error=str(exc)[:180])
        return
    if MODE == 'paper':
        log('paper_sim', user=user, loan_wei=loan, gross_wei=final_gross,
            gas_limit=gas_limit, max_fee=max_fee, cap_wei=cap, result='success')
    else:
        log('send', user=user, loan_wei=loan, gross_wei=final_gross,
            gas_limit=gas_limit, max_fee=max_fee, cap_wei=cap)
        send_live(user, loan, final_gross, cap, gas_limit, max_fee, min_profit)

def main():
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC,
        controller=CTRL, poll_seconds=POLL_SECONDS)
    retry_after, fails = {}, {}
    loans, loans_at = [], 0.0
    fast_day, fast_used, last_scan_log, was_near = '', 0, 0.0, False
    while True:
        near = False
        try:
            now = time.time()
            if now - loans_at > LOANS_REFRESH_SECONDS:
                loans = borrowers()
                loans_at = now
                log('loans', count=len(loans))
            rows = healths(loans) if loans else []
            seen = [(u, h) for u, h in rows if h < 0]
            positive = [h for _, h in rows if h >= 0]
            min_pos = min(positive) if positive else None
            near = min_pos is not None and min_pos < NEAR_HEALTH
            if near != was_near or now - last_scan_log >= POLL_SECONDS:
                log('scan', loans=len(rows), unhealthy=len(seen), min_positive_health=min_pos, near=near, fast_used=fast_used)
                last_scan_log, was_near = now, near
            for user, health in seen:
                if now < retry_after.get(user, 0):
                    continue
                check_user(user, health)
                # back off per borrower: 5 min, doubling to 1 h (a bad-debt position stays under zero for days)
                fails[user] = min(fails.get(user, 0) + 1, 5)
                retry_after[user] = now + min(SEND_RETRY_SECONDS * 2 ** (fails[user] - 1), 3600)
            for user in [u for u in fails if u not in {s[0] for s in seen}]:
                del fails[user]
        except BudgetError as exc:
            log('read_budget', error=str(exc))
            time.sleep(3600)
        except Exception as exc:
            log('scan_error', error=str(exc)[:200])
        # A borrower just above zero health: poll every FAST_SECONDS, at most FAST_POLLS_PER_DAY times per UTC day.
        day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        if day != fast_day:
            fast_day, fast_used = day, 0
        if near and fast_used < FAST_POLLS_PER_DAY:
            fast_used += 1
            time.sleep(FAST_SECONDS)
        else:
            time.sleep(POLL_SECONDS)

if __name__ == '__main__':
    main()
