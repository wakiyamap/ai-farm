#!/usr/bin/env python3
"""trial: wstEP FBX auction on Polygon. WrappedStakedEP (wstEP, 0xe3df997c..., ownerless, verified) stakes EP and
sells the FBX that staking pays through a public curve: takeAuction(amountEP, minFbxOut) pays
fbxPool * amountEP / (amountEP + 9 EP) FBX for amountEP EP, to anyone. The FBX book grows with accrual (about
15 FBX an hour), so its marginal rate fbxPool / 9 climbs above the EP price on the SushiSwap EP / FBX pair
(0x41d9de53...). One transaction through the CurveAuctionArb executor then: flash swap EP out of the Sushi pair ->
takeAuction -> repay the pair in FBX -> sell the FBX left (Uniswap V2 FBX / USDT, QuickSwap USDT / WPOL) -> unwrap ->
pay the bot wallet in POL. The executor reverts unless the wallet is paid at least minProfit.
Timer bot: one eth_call of the executor's probe() (a grid of sizes) every POLL seconds; accrual is the clock, so there
is no event to wait for. It sends when the best size pays MIN_GROSS_WEI and more than 1.3 x the send's cost cap."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545').rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'polygon'

# Addresses: the receipt of incumbent take 0xe9458b54b814e7e2c66336a1cf26638ea7f79983c5122540cbdb1579965a85b8, the
# vault's verified source (EP / FBX constants) and its EP() / FBX() getters, token0() / token1() / factory() of the
# three pairs, read on 2026-11-22 (scratch/trial-wstep-auction-polygon/state.py, state.json).
VAULT = '0xe3df997cad0476954196fdfe94a9bc090365cad9'        # WrappedStakedEP: takeAuction(uint256,uint256)
EP = '0x60ed6acef3a96f8cdaf0c0d207bbafa66e751af2'           # Elemental Particles, the token the auction is paid in
FBX = '0xd125443f38a69d776177c2b9c041f462936f8218'          # FireBotToken, the token the auction pays out
PAIR = '0x41d9de53ebf26f766229e42aa02904eb2495e397'         # SushiSwap V2 EP (token0) / FBX (token1), 0.3 pct
EXIT1 = '0x1000bb854fbc6d98dc9d859d6cb47e22a31eb8f9'        # Uniswap V2 USDT (token0) / FBX (token1), 0.3 pct
USDT = '0xc2132d05d31c914a87c6611c10748aeb04b58e8f'
EXIT2 = '0x604229c960e5cacf2aaeac8be68ac07ba9df81c3'        # QuickSwap V2 WPOL (token0) / USDT (token1), 0.3 pct
WPOL = '0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270'
FEE1000 = 997
# EP sizes probed each look: 0.02 x 1.25^k, k = 0..17 (0.02 .. 0.89 EP; the incumbent takes 0.5 EP, the best size
# at its take times was about 0.25 EP)
SIZES = [int(2 * 10**16 * 1.25**k) for k in range(18)]

# Selectors and topics from `cast sig` / `cast keccak` (checked again by scratch/trial-wstep-auction-polygon/proof.py).
TAKE_TYPES = '(address,address,address,address,uint256,uint256,address,uint256,address,address,uint256,address,uint256)'
SEL_TAKE = '0x78f097d3'    # take(TAKE_TYPES)
SEL_PROBE = '0x6ecf63a3'   # probe(TAKE_TYPES[])
TOPIC_TAKEN = '0x4c7da8eb46627ba04a1791574ac8c982e12a07400f55df199032495f4dd540b5'   # AuctionTaken(address,uint256,uint256)

PAPER_EXEC = '0x00000000000000000000000000000000000f11ab'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_POLYGON') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_POLYGON or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

POLL = 120                         # seconds between looks (720 looks a day x 26 CU = 18,720 CU)
POLL_AFTER_SEND = 20               # one look soon after a send or a standing gain
MIN_INTEREST_WEI = 3 * 10**17      # 0.3 POL (about 0.02 USD): below this nothing is logged
MIN_GROSS_WEI = 10 * 10**17        # 1.0 POL (about 0.075 USD, 3-4 x a send's cost cap): the gain grows with the square
#                                    of the wait, so do not take the first cent; the incumbent's 0.5 EP takes every
#                                    5.5-6 h reset the book, and once this bot also takes, a cycle peaks near 1.1-1.4 POL
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # and send only when gross > 1.3 x the send's cost cap
TIP_SHARE_DEN = 10                 # priority fee: at most 1/10 of gross spread over the gas limit ...
TIP_MAX_WEI = 60 * 10**9           # ... and never above 60 gwei (the one other taker runs on a timer, not on fees)
TIP_MIN_WEI = 40 * 10**9           # Polygon validators want 25-30 gwei at least
MAX_FEE_CAP_WEI = 1500 * 10**9     # never sign above 1500 gwei
GAS_LIMIT_MAX = 1_200_000          # eth_estimateGas says 0.56-0.70M (a take uses about 0.44M); x 1.2 on top
POL_REF_USD = 0.5                  # deliberately high POL price for the USD cap (POL was 0.075 USD on 2026-11-22)
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


def take_tuple(amount, min_profit):
    """ABI encoding of one Take struct (static: 13 words)."""
    return (a(VAULT) + a(EP) + a(FBX) + a(PAIR) + w(FEE1000) + w(amount) + a(EXIT1) + w(FEE1000) + a(USDT) + a(EXIT2)
            + w(FEE1000) + a(WPOL) + w(min_profit))


def take_calldata(amount, min_profit):
    return SEL_TAKE + take_tuple(amount, min_profit)


def probe_calldata(sizes):
    return SEL_PROBE + w(32) + w(len(sizes)) + ''.join(take_tuple(s, 1) for s in sizes)


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


def probe(sizes, block='latest'):
    """Gains (wei of POL) of each size on chain in ONE eth_call; 0 = that take would revert."""
    res = rpc('eth_call', call_params(probe_calldata(sizes), None, block)).removeprefix('0x')
    words = [int(res[i:i + 64], 16) for i in range(0, len(res), 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(sizes):
        raise RuntimeError('probe: unexpected return length')
    return gains


def gain_of(amount, min_profit, gas_limit=None):
    """Return value of the exact take() as an eth_call; 0 when it reverts."""
    ans = rpc('eth_call', call_params(take_calldata(amount, min_profit), gas_limit), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def last_take_block(block):
    """Block of the newest AuctionTaken on the vault near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': VAULT, 'fromBlock': hex(block - 300), 'toBlock': hex(block + 5),
                                'topics': [TOPIC_TAKEN]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(amount, gross, cap, max_fee, tip, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(amount, cap), 0, gas_limit, max_fee,
                                max_priority_fee_per_gas=tip)
    tx_hash = reply.get('txHash') if isinstance(reply, dict) else None
    if not tx_hash:
        log('signer_reject', reply=reply)
        return
    receipt = None
    for _ in range(20):
        time.sleep(2)
        receipt = rpc('eth_getTransactionReceipt', [tx_hash])
        if receipt:
            break
    common = dict(hash=tx_hash, amount_ep_wei=amount, expected_gross_wei=gross, cap_wei=cap,
                  gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        winner = block if status else last_take_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        net_wei=(gross - cost) if status else -cost, send_block=block, winner_block=winner,
        tx_index=int(receipt['transactionIndex'], 16), **common)


def check():
    """One look: 1 eth_call when nothing is open. Returns True when a gain above MIN_GROSS was seen."""
    gains = probe(SIZES)
    gross = max(gains)
    if gross < MIN_INTEREST_WEI:
        return False
    amount = SIZES[gains.index(gross)]
    if gross < MIN_GROSS_WEI:
        log('building', amount_ep_wei=amount, gross_wei=gross, min_gross_wei=MIN_GROSS_WEI)
        return False
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(take_calldata(amount, 1))), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', amount_ep_wei=amount, gross_wei=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 12 // 10
    tip = max(TIP_MIN_WEI, min(TIP_MAX_WEI, gross // TIP_SHARE_DEN // gas_limit))
    max_fee = base_fee + base_fee // 4 + tip
    cap = gas_limit * max_fee                          # the most this send can cost (maxFeePerGas x gasLimit)
    cap_usd = cap / 1e18 * POL_REF_USD
    log('opportunity', amount_ep_wei=amount, gross_wei=gross, gains_wei=gains, cap_wei=cap,
        base_fee=base_fee, tip_wei=tip, max_fee_wei=max_fee, gas_estimate=estimate, gas_limit=gas_limit,
        cap_usd=round(cap_usd, 4))
    if max_fee > MAX_FEE_CAP_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', max_fee_wei=max_fee, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross * SEND_MULT_DEN <= cap * SEND_MULT_NUM:   # send only when expected gross > 1.3 x this send's cost cap
        log('opportunity_skip', reason='gross_below_send_line', gross_wei=gross, cap_wei=cap)
        return True
    checked, err = gain_of(amount, cap, gas_limit)     # the exact call that would be signed (minProfit = cap)
    if checked <= cap:
        log('simulate_revert', step='guard', amount_ep_wei=amount, gross_wei=gross, cap_wei=cap, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', amount_ep_wei=amount, gross_wei=checked, cap_wei=cap,
            gas_estimate=estimate, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    else:
        send_live(amount, checked, cap, max_fee, tip, gas_limit)
    return True


def main():
    """Look every POLL seconds. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), vault=VAULT, pair=PAIR, exit_pairs=[EXIT1, EXIT2], sizes=len(SIZES),
        trigger='timer', poll_seconds=POLL, min_gross_wei=MIN_GROSS_WEI)
    looks = 0
    while True:
        wait = POLL
        try:
            looks += 1
            standing = check()
            if standing:
                wait = POLL_AFTER_SEND if MODE == 'live' else POLL
            elif looks % 30 == 1:
                log('heartbeat', looks=looks)
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            wait = 86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 5   # to 00:00 UTC
        except Exception as e:
            log('loop_error', error=str(e)[:250])
        time.sleep(wait)


if __name__ == '__main__':
    main()
