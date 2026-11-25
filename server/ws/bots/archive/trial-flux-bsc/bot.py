#!/usr/bin/env python3
"""Trial for the public Fluid BNB/USDC vault liquidation on BSC.

Every 30 seconds, quote the currently liquidatable debt with Fluid's documented
revert-quote recipient. A positive quote is checked by executing the exact
flash-funded executor call as eth_call. Live sends go only through the signer.
"""
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
CHAIN = 'bsc'
VAULT = '0xeAbBfca72F8a8bf14C4ac59e69ECB2eB69F0811C'
USDC = '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d'
WBNB = '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'
FLASH = '0x6807dc923806fe8fd134338eabca509979a7e0cb'
POOL = '0xf2688fb5b81049dfb7703ada5e770543770612c4'
ORACLE = '0x39bc1bfDa2130d6Bb6DBEfd366939b4c7aa7C697'
# All four selectors were generated with cast sig/calldata; LogLiquidate topic with cast keccak.
SEL_QUOTE = '0x8433ea22'
SEL_TAKE = '0x6fab7c4b'
SEL_PRICE = '0xb3596f07'
T_LIQUIDATE = '0x80fd9cc6b1821f4a510e45ffce6852ea3404807b5d3d833ffa85664408afcb66'
ERR_RESULT = '0xcc36aa44'
PAPER_EXEC = '0x8f7a45ebde059392e46a46dcc14ab24681a961ea'
PAPER_OWNER = '0x1111111111111111111111111111111111111111'
EXEC = os.environ.get('EXECUTOR_ADDR_BSC') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BSC or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x'):
    raise SystemExit('paper executor runtime missing')
LOG = HERE / 'logs' / 'bot.jsonl'
CU_STATE = HERE / 'state' / 'cu.json'
SEND_STATE = HERE / 'state' / 'send.json'
LOG.parent.mkdir(exist_ok=True)
CU_STATE.parent.mkdir(exist_ok=True)
CU_COST = {'eth_call': 26, 'eth_gasPrice': 10, 'eth_getTransactionReceipt': 20,
           'eth_getLogs': 75, 'eth_blockNumber': 10}
CU_CAP = 90000
POLL_SECONDS = 30
COOLDOWN_SECONDS = 120
GAS_LIMIT = 1200000
LOSS_CAP_USD = 0.85
BID_SHARE = 0.25
MAX_DEBT = 400 * 10**18
_id = 0

def log(ev, **kw):
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': time.time(), 'ev': ev, **kw}, separators=(',', ':'), default=str) + '\n')

def aw(a):
    return a.lower().removeprefix('0x').zfill(64)

def word(n):
    return format(int(n), '064x')

def rpc(method, params):
    global _id
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(CU_STATE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    cost = CU_COST.get(method, 26)
    if budget['cu'] + cost > CU_CAP:
        raise RuntimeError('read budget exhausted')
    budget['cu'] += cost
    CU_STATE.write_text(json.dumps(budget))
    _id += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)

def quote_data(debt):
    # cast calldata liquidate(uint256,uint256,address,bool) debt 0 0x...dEaD false
    return SEL_QUOTE + word(debt) + word(0) + aw('0x000000000000000000000000000000000000dEaD') + word(0)

def take_data(debt, min_profit):
    # cast calldata take((address,address,address,address,address,uint256,uint256,uint256,bool)) (flash,vault,usdc,wbnb,pool,debt,0,min_profit,false)
    return SEL_TAKE + ''.join(map(aw, (FLASH, VAULT, USDC, WBNB, POOL))) + word(debt) + word(0) + word(min_profit) + word(0)

def quote():
    ans = rpc('eth_call', [{'from': PAPER_OWNER, 'to': VAULT, 'data': quote_data(MAX_DEBT), 'gas': hex(GAS_LIMIT)}, 'latest'])
    err = ans.get('error') or {}
    data = err.get('data', '')
    if data.startswith(ERR_RESULT) and len(data) >= 138:
        collateral = int(data[10:74], 16)
        debt = int(data[74:138], 16)
        return debt, collateral
    if err:
        code = data[:10]
        if code not in ('0x60121cca', ''):
            log('quote_error', code=code, message=err.get('message', '')[:120])
        return None
    log('quote_unexpected', result=ans.get('result', '')[:80])
    return None

def bnb_price():
    ans = rpc('eth_call', [{'to': ORACLE, 'data': SEL_PRICE + aw(WBNB)}, 'latest'])
    if 'error' in ans:
        raise RuntimeError(str(ans['error']))
    price = int(ans['result'], 16) / 1e8
    if not (100 <= price <= 10000):
        raise RuntimeError(f'bad BNB oracle price {price}')
    return price

def simulate(debt, from_addr, executor, code):
    data = take_data(debt, 1)
    params = [{'from': from_addr, 'to': executor, 'data': data, 'gas': hex(GAS_LIMIT)}, 'latest']
    if code:
        params.append({executor: {'code': code}})
    ans = rpc('eth_call', params)
    if 'error' in ans:
        log('sim_revert', debt=debt, error=str(ans['error'])[:250])
        return 0
    return int(ans['result'], 16)

def owner():
    import farmbot_signer
    result = farmbot_signer.my_address()
    address = result['address']
    if not isinstance(address, str) or len(address) != 42:
        raise RuntimeError('signer returned no owner address')
    return address

def winner_block(txhash, block):
    if block is None:
        return None
    lo = max(0, block - 1000)
    hi = max(block, int(rpc('eth_blockNumber', [])['result'], 16))
    logs = rpc('eth_getLogs', [{'address': VAULT, 'fromBlock': hex(lo), 'toBlock': hex(hi), 'topics': [T_LIQUIDATE]}])
    if 'error' in logs:
        return None
    matches = [int(x['blockNumber'], 16) for x in logs['result'] if x['transactionHash'].lower() == txhash.lower()]
    if matches:
        return min(matches)
    return min((int(x['blockNumber'], 16) for x in logs['result']), default=None)

def live_send(data, gross, gas_price, price):
    import farmbot_signer
    price_guard = price * 1.2
    cap_wei = int(LOSS_CAP_USD * 1e18 / (price_guard * GAS_LIMIT))
    gross_usd = gross / 1e18
    bid_wei = int(gross_usd * BID_SHARE * 1e18 / (price_guard * GAS_LIMIT))
    max_fee = min(cap_wei, max(gas_price * 2, bid_wei))
    if max_fee < gas_price or max_fee <= 0:
        log('opportunity_skip', reason='gas_price_above_cap', gas_price=gas_price, cap_wei=cap_wei)
        return
    gas_cap_usd = max_fee * GAS_LIMIT * price_guard / 1e18
    if gross_usd <= gas_cap_usd:
        log('opportunity_skip', reason='gross_below_gas_cap', gross_usd=gross_usd, gas_cap_usd=gas_cap_usd)
        return
    # BSC head reports baseFeePerGas=0, so the offered gas price is the priority bid.
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, GAS_LIMIT, max_fee, max_priority_fee_per_gas=max_fee)
    h = reply.get('txHash') if isinstance(reply, dict) else None
    if not h:
        log('signer_reject', reply=reply)
        return
    receipt = None
    for _ in range(30):
        time.sleep(1)
        ans = rpc('eth_getTransactionReceipt', [h])
        if 'error' not in ans and ans.get('result'):
            receipt = ans['result']
            break
    if not receipt:
        log('send_result', hash=h, result='unknown', gas_used=None, winner_block=None)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    eff = int(receipt.get('effectiveGasPrice', '0x0'), 16)
    try:
        winner = winner_block(h, block)
    except Exception as e:
        winner = None
        log('winner_lookup_error', error=str(e)[:200])
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * eff, send_block=block, winner_block=winner,
        blocks_from_winner=None if winner is None else block - winner)

def check():
    q = quote()
    if not q:
        return
    debt, collateral = q
    if debt <= 0 or debt > MAX_DEBT:
        return
    from_addr = owner() if MODE == 'live' else PAPER_OWNER
    executor = EXEC if MODE == 'live' else PAPER_EXEC
    code = None if MODE == 'live' else RUNTIME
    gross = simulate(debt, from_addr, executor, code)
    if gross <= 0:
        return
    price = bnb_price()
    gas_ans = rpc('eth_gasPrice', [])
    if 'error' in gas_ans:
        raise RuntimeError(str(gas_ans['error']))
    gas_price = int(gas_ans['result'], 16)
    cap_wei = int(LOSS_CAP_USD * 1e18 / (price * 1.2 * GAS_LIMIT))
    bid_wei = int((gross / 1e18) * BID_SHARE * 1e18 / (price * 1.2 * GAS_LIMIT))
    max_fee = min(cap_wei, max(gas_price * 2, bid_wei))
    gas_cap_usd = max_fee * GAS_LIMIT * price * 1.2 / 1e18
    log('opportunity', debt=debt, collateral=collateral, gross_usdc=gross,
        gas_price=gas_price, max_fee=max_fee, gas_cap_usd=gas_cap_usd,
        executor=executor, mode=MODE)
    if max_fee < gas_price or gross / 1e18 <= gas_cap_usd:
        log('opportunity_skip', reason='gas_cap_or_gross')
        return
    min_profit = int(gas_cap_usd * 1e18) + 1
    data = take_data(debt, min_profit)
    if MODE == 'paper':
        log('paper_send', debt=debt, gross_usdc=gross, min_profit=min_profit,
            max_fee=max_fee, gas_limit=GAS_LIMIT, result='simulated')
    else:
        live_send(data, gross, gas_price, price)

def main():
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, poll_seconds=POLL_SECONDS)
    while True:
        try:
            now = time.time()
            try:
                s = json.loads(SEND_STATE.read_text())
            except Exception:
                s = {'last_positive': 0}
            if now - s.get('last_positive', 0) >= COOLDOWN_SECONDS:
                before = LOG.stat().st_size if LOG.exists() else 0
                check()
                # A positive opportunity is logged; throttle repeats around one auction.
                with LOG.open() as f:
                    f.seek(before)
                    new = f.read()
                if '"ev":"opportunity"' in new:
                    SEND_STATE.write_text(json.dumps({'last_positive': now}))
        except Exception as e:
            log('error', message=str(e)[:300])
        time.sleep(POLL_SECONDS)

if __name__ == '__main__':
    main()
