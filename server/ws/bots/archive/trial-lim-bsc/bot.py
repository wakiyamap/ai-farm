#!/usr/bin/env python3
"""Trial: poll DODO Lim/USDT quotes and simulate an atomic Infinity arbitrage."""
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
POOLS = ('0x7e782d59aa7598e706c3e3bae73828ecdd4e1075', '0x4976ae418f7de1674acd01a8029805fc55bbc455')
VAULT = '0x238a358808379702088667322f80ac48bad5e6c4'
MANAGER = '0xa0ffb9c1ce1fe56963b0321b32e7a0302114058b'
HOOK = '0x2f531df08c645169b303abe94797b47c746d699f'
LIM = '0x1d6430fdfc63ea481fe157017b47530663c96001'
USDT = '0x55d398326f99059ff775485246999027b3197955'
USDC = '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d'
PAIR = '0xec6557348085aa57c72514d67070dc863c0a5a8c'
PARAMETERS = int('3c0041', 16)
LIMIT = int('1000276a4', 16)
QUOTE_IN = 75 * 10**18
POLL_SECONDS = 60  # alternate two pools: each pool every two minutes
PAPER_OWNER = '0x1111111111111111111111111111111111111111'
PAPER_EXEC = '0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352'
EXEC = os.environ.get('EXECUTOR_ADDR_BSC') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BSC or EXECUTOR_ADDR is required in live mode')
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip()
if not RUNTIME.startswith('0x') or len(RUNTIME) < 100:
    raise SystemExit('missing paper executor runtime')

LOG = HERE / 'logs/bot.jsonl'
CU_PATH = HERE / 'state/cu.json'
LOG.parent.mkdir(exist_ok=True)
CU_PATH.parent.mkdir(exist_ok=True)
CU_CAP = 90_000
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_gasPrice': 20,
           'eth_getTransactionReceipt': 20, 'eth_getLogs': 60}
BNB_USD_CEILING = 1000  # conservative trial gas valuation; signer enforces its live Chainlink price
MAX_FEE_WEI = 400_000_000
MAX_GAS_LIMIT = 900_000
MAX_TX_USD = 0.80
MAX_BID_SHARE = 0.50
_id = 0


class ReadBudgetExceeded(Exception):
    pass


def log(event, **fields):
    with LOG.open('a') as f:
        f.write(json.dumps({'ts': time.time(), 'ev': event, **fields}, separators=(',', ':')) + '\n')


def rpc(method, params):
    global _id
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(CU_PATH.read_text())
    except (OSError, ValueError):
        budget = {'day': today, 'cu': 0}
    if budget['day'] != today:
        budget = {'day': today, 'cu': 0}
    cost = CU_COST.get(method, 26)
    if budget['cu'] + cost > CU_CAP:
        raise ReadBudgetExceeded(f'{CU_CAP} CU/day cap')
    budget['cu'] += cost
    CU_PATH.write_text(json.dumps(budget))
    _id += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{CHAIN}?lane={LANE}', body,
                                 {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=25) as response:
        ans = json.load(response)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:400]}')
    return ans['result']


def word(n):
    return f'{int(n):064x}'


def address_word(a):
    return a.lower()[2:].zfill(64)


def query(pool, owner, block='latest'):
    # cast sig querySellQuote(address,uint256) = 0x66410a21
    data = '0x66410a21' + address_word(owner) + word(QUOTE_IN)
    raw = rpc('eth_call', [{'from': owner, 'to': pool, 'data': data}, block])
    if len(raw) < 66:
        raise RuntimeError('short DODO quote')
    return int(raw[2:66], 16)


def calldata(pool, amount, min_profit=1):
    # cast sig take(address,address,address,address,address,address,address,address,
    # uint24,bytes32,uint16,uint256,uint256,uint160,uint256) = 0x44139938
    return '0x44139938' + ''.join((
        address_word(pool), address_word(VAULT), address_word(MANAGER), address_word(HOOK),
        address_word(LIM), address_word(USDT), address_word(USDC), address_word(PAIR),
        word(0x800000), word(PARAMETERS), word(9970), word(amount), word(QUOTE_IN),
        word(LIMIT), word(min_profit)))


def sim_params(owner, pool, amount, min_profit=1, block='latest'):
    tx = {'from': owner, 'to': EXEC if MODE == 'live' else PAPER_EXEC,
          'data': calldata(pool, amount, min_profit)}
    params = [tx, block]
    if MODE == 'paper':
        params.append({PAPER_EXEC: {'code': RUNTIME}})
    return params


def evaluate(pool, owner, block='latest'):
    amount = query(pool, owner, block)
    if amount <= 0:
        return amount, 0
    raw = rpc('eth_call', sim_params(owner, pool, amount, 1, block))
    if len(raw) < 66:
        raise RuntimeError('short executor simulation')
    return amount, int(raw, 16)


def owner_address():
    if MODE == 'paper':
        return PAPER_OWNER
    import farmbot_signer
    ans = farmbot_signer.my_address()
    if not isinstance(ans, dict) or not ans.get('ok') or not ans.get('address'):
        raise RuntimeError(f'bad signer my_address: {ans}')
    return ans['address']


def winner(pool, block, own_hash):
    # cast keccak DODOFlashLoan(address,address,uint256,uint256)
    topic = '0x0b82e93068db15abd9fbb2682c65462ea8a0a10582dce93a5664818e296f54eb'
    lo = max(0, block - 3)
    logs = rpc('eth_getLogs', [{'address': pool, 'topics': [topic],
                                'fromBlock': hex(lo), 'toBlock': hex(block)}])
    others = [x for x in logs if x['transactionHash'].lower() != own_hash.lower()]
    if not others:
        return None, None
    last = others[-1]
    return int(last['blockNumber'], 16), last['transactionHash']


def send_live(pool, owner, amount, gross, gas_price, gas_limit, gas_cap):
    import farmbot_signer
    min_profit = int(gas_cap * 10**18) + 1
    data = calldata(pool, amount, min_profit)
    ans = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, gas_price,
                              max_priority_fee_per_gas=gas_price)
    tx_hash = (ans.get('txHash') or ans.get('tx_hash') or ans.get('hash')) if isinstance(ans, dict) else None
    if not tx_hash:
        log('signer_reject', pool=pool, reply=ans)
        return
    log('send', pool=pool, hash=tx_hash, executor=EXEC, gross_usdc=gross,
        gas_limit=gas_limit, max_fee=gas_price, gas_cap_usd=gas_cap)
    receipt = None
    for _ in range(30):
        time.sleep(1)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    if not receipt:
        log('send_result', pool=pool, hash=tx_hash, result='unknown', gas_used=None,
            winner_block=None)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    gas_used = int(receipt['gasUsed'], 16)
    try:
        winner_block, winner_hash = winner(pool, block, tx_hash)
    except Exception as exc:
        log('winner_lookup_error', error=str(exc)[:200])
        winner_block = winner_hash = None
    log('send_result', pool=pool, hash=tx_hash, result='won' if status else 'lost',
        gas_used=gas_used, gas_cost_wei=gas_used * int(receipt['effectiveGasPrice'], 16),
        send_block=block, winner_block=winner_block, winner_tx=winner_hash,
        blocks_after_winner=(block-winner_block if winner_block is not None else None))


def attempt(pool, owner, block='latest'):
    try:
        amount, gross = evaluate(pool, owner, block)
    except ReadBudgetExceeded:
        raise
    except Exception as exc:
        log('simulate_revert', pool=pool, error=str(exc)[:300])
        return
    if gross <= 0:
        return
    log('opportunity', pool=pool, amount_lim=amount, gross_usdc=gross, block=block)
    price = int(rpc('eth_gasPrice', []), 16)
    gas_limit = 650_000
    if MODE == 'live':
        try:
            estimate = int(rpc('eth_estimateGas', sim_params(owner, pool, amount, 1, block)[:2]), 16)
            gas_limit = max(estimate * 5 // 4, 550_000)
            if gas_limit > MAX_GAS_LIMIT:
                log('opportunity_skip', pool=pool, gross_usd=gross / 1e18,
                    gas_limit=gas_limit, reason='gas_limit')
                return
        except Exception as exc:
            log('estimate_error', pool=pool, error=str(exc)[:300])
            return
    gas_price = min(price, MAX_FEE_WEI)
    gas_cap = gas_limit * gas_price * BNB_USD_CEILING / 1e18
    gross_usd = gross / 1e18
    if gas_price < price or gas_cap > MAX_TX_USD or gas_cap >= gross_usd or gas_cap > gross_usd * MAX_BID_SHARE:
        log('opportunity_skip', pool=pool, gross_usd=gross_usd, gas_cap_usd=gas_cap,
            gas_price=gas_price, node_price=price, reason='gas_or_bid')
        return
    if MODE == 'paper':
        log('paper_sim', pool=pool, gross_usdc=gross, gas_cap_usd=gas_cap, gas_limit=gas_limit)
        return
    send_live(pool, owner, amount, gross, gas_price, gas_limit, gas_cap)


def sleep_until_utc_midnight():
    now = datetime.datetime.now(datetime.timezone.utc)
    next_day = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
    time.sleep(max(1, (next_day - now).total_seconds()))


def main():
    idx = 0
    while True:
        try:
            owner = owner_address()
            if idx == 0:
                log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC,
                    owner=owner, poll_seconds=POLL_SECONDS)
            attempt(POOLS[idx % len(POOLS)], owner)
            idx += 1
            time.sleep(POLL_SECONDS)
        except ReadBudgetExceeded as exc:
            log('read_budget', error=str(exc))
            sleep_until_utc_midnight()
        except Exception as exc:
            log('loop_error', error=str(exc)[:400])
            time.sleep(20)


if __name__ == '__main__':
    main()
