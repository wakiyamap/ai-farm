#!/usr/bin/env python3
"""trial: MDB+ (BSC) mint / redeem at its BUSD backing value versus the PancakeSwap V2 ESHARE / MDB+ pair.
MDB+ 0x9f8bb16f is a token backed by BUSD held in the token contract: sell(amount) burns it and pays
backing / supply per token, mintWithBacking(busd, to) mints at the same value, both open to anyone
(verified source on Sourcify; all four fees are 0 at placement). Its only pool is priced in ESHARE, and ESHARE in
WBNB, so the pool price drifts away from the backing value whenever BNB moves against BUSD or somebody trades.
One transaction through the StepArb executor, funded by a free WBNB flash loan from Lista Moolah:
  redeem: WBNB -> ESHARE -> MDB+ (router) -> MDB+.sell -> BUSD -> WBNB (router) -> repay -> the rest as BNB to the wallet
  mint:   WBNB -> BUSD (router) -> MDB+.mintWithBacking -> MDB+ -> ESHARE -> WBNB (router) -> repay -> the rest as BNB
take() reverts unless the WBNB left after repayment is at least minProfit.
Timer bot: one probe() eth_call every POLL seconds (both directions, 8 sizes each, the exact transactions simulated)."""
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
RELAY = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545').rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'bsc'

# Addresses: receipts of the incumbent takes (scratch/r63f9/takes.json), token0() / token1() / factory() of the pairs,
# MDB+ underlying() and its verified source (router constant), Moolah from the take trace 0x69655c38... and
# protocols:558; scratch/trial-mdb-nav-bsc/proof.py asserts them again on the fork by their getters.
MDB = '0x9f8bb16f49393eea4331a39b69071759e54e16ea'          # MDB+ token: sell(uint256), mintWithBacking(uint256,address)
BUSD = '0xe9e7cea3dedca5984780bafc599bd69add087d56'         # MDB+.underlying()
WBNB = '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'
ESHARE = '0xdb20f6a8665432ce895d724b417f77ecac956550'
ROUTER = '0x10ed43c718714eb63d5aa57b78b54704e256024e'       # PancakeSwap V2 router (the constant in MDB+'s source)
MOOLAH = '0x8f73b65b4caaf64fba2af91cc5d4a2a1318e5d8c'       # Lista Moolah: flashLoan(token, assets, data), no fee,
#                                                             callback onMoolahFlashLoan(uint256,bytes)
PAIR_ESHARE_MDB = '0x51586182a2031f3e384d080f78c8836d48ebbffc'    # the only MDB+ pool the takers use
PAIR_WBNB_ESHARE = '0x1747af98ebf0b22d500014c7dd52985d736337d2'
# WBNB flashed each look: 0.0006 x 1.7^k, k = 0..7 (0.0006 .. 0.0246 WBNB; incumbent takes were 0.0024-0.009 WBNB)
SIZES = [int(6 * 10**14 * 1.7**k) for k in range(8)]
DIRECTIONS = ('redeem', 'mint')

# Selectors and topics from `cast sig` / `cast keccak` (asserted again by proof.py).
SEL_TAKE = '0x13b75307'      # take(address,address,uint256,(address,address,address,uint256,uint256,bytes)[],address[],uint256,bool)
SEL_PROBE = '0x8ad8bbaf'     # probe(bytes[])
SEL_SWAP = '0x5c11d795'      # swapExactTokensForTokensSupportingFeeOnTransferTokens(uint256,uint256,address[],address,uint256)
SEL_SELL = '0xe4849b32'      # sell(uint256)
SEL_MINT = '0x7314f109'      # mintWithBacking(uint256,address)
TOPIC_REDEEMED = '0xf3a670cd3af7d64b488926880889d08a8585a138ff455227af6737339a1ec262'   # Redeemed(address,uint256,uint256)
TOPIC_MINTED = '0x30385c845b448a36257a6a1716e6ad2e1bc2cbe333cde1e69fe849ad6511adfe'     # Minted(address,uint256)
DEADLINE = 2**256 - 1

PAPER_EXEC = '0x00000000000000000000000000000000000f11b5'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_BSC') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_BSC or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

POLL = 60                          # seconds between looks: the gap opens with the BNB / BUSD price, not with an event
#                                    on a quiet address (0 swaps on both ESHARE pairs in the 24 h before placement)
FOLLOW_UPS = (3, 10, 30)           # extra looks after a look that saw a gain (a send that lost, a gap still open)
MIN_INTEREST_WEI = 2 * 10**13      # 0.00002 BNB (about 0.01 USD): below this nothing is logged
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send only when gross > 1.3 x the send's cost cap
TIP_SHARE_DEN = 3                  # gas price bid: at most 1/3 of gross spread over the gas limit ...
GAS_PRICE_MAX_WEI = 6 * 10**8      # ... and never above 0.6 gwei (the BSC floor is 0.05 gwei)
GAS_LIMIT_MAX = 1_500_000          # a take uses about 0.45-0.6M gas; eth_estimateGas x 1.25 on top
BNB_REF_USD = 1500.0               # deliberately high BNB price for the USD cap (BNB was about 560 BUSD on 2026-11-23)
MAX_TX_USD = 0.95
CU_CAP = 95_000
CU_COST = {'eth_call': 26, 'eth_gasPrice': 10, 'eth_estimateGas': 20, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_getLogs': 75}

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


# ---- ABI encoding (static words and the one dynamic shape take() needs) ----
def w(n):
    return format(n, '064x')


def a(addr):
    return addr.lower().removeprefix('0x').zfill(64)


def step(target, token_in, spender, data, offset):
    return {'target': target, 'tokenIn': token_in, 'spender': spender or '0x' + '00' * 20, 'amount': 0,
            'offset': offset, 'data': data}


def swap_data(path, to):
    """Router swap of the step's whole tokenIn balance along `path`; the amount is written at byte 4 by StepArb."""
    return SEL_SWAP + w(0) + w(0) + w(5 * 32) + a(to) + w(DEADLINE) + w(len(path)) + ''.join(a(t) for t in path)


def route_steps(direction, to):
    if direction == 'redeem':
        return [
            step(ROUTER, WBNB, ROUTER, swap_data([WBNB, ESHARE, MDB], to), 4),
            step(MDB, MDB, None, SEL_SELL + w(0), 4),                      # burns the executor's MDB+, pays BUSD
            step(ROUTER, BUSD, ROUTER, swap_data([BUSD, WBNB], to), 4),
        ]
    return [
        step(ROUTER, WBNB, ROUTER, swap_data([WBNB, BUSD], to), 4),
        step(MDB, BUSD, MDB, SEL_MINT + w(0) + a(to), 4),                  # mints MDB+ to the executor
        step(ROUTER, MDB, ROUTER, swap_data([MDB, ESHARE, WBNB], to), 4),
    ]


CLEAR = [ESHARE, MDB, BUSD]       # leftovers of these go to the owner at the end of take() (normally 0)


def enc_step(s):
    data = bytes.fromhex(s['data'].removeprefix('0x'))
    pad = (-len(data)) % 32
    return (a(s['target']) + a(s['tokenIn']) + a(s['spender']) + w(s['amount']) + w(s['offset'])
            + w(6 * 32) + w(len(data)) + data.hex() + '00' * pad)


def take_calldata(direction, amount, min_profit, executor_addr):
    steps = [enc_step(s) for s in route_steps(direction, executor_addr)]
    offs, pos = [], 32 * len(steps)
    for s in steps:
        offs.append(pos)
        pos += len(s) // 2
    steps_blob = w(len(steps)) + ''.join(w(o) for o in offs) + ''.join(steps)
    clear_blob = w(len(CLEAR)) + ''.join(a(t) for t in CLEAR)
    head = 7 * 32
    # unwrap = true: the WBNB left after repayment is unwrapped and paid to the owner as BNB
    return (SEL_TAKE + a(MOOLAH) + a(WBNB) + w(amount) + w(head) + w(head + len(steps_blob) // 2)
            + w(min_profit) + w(1) + steps_blob + clear_blob)


def probe_calldata(calls):
    blobs = []
    for c in calls:
        raw = c.removeprefix('0x')
        blobs.append(w(len(raw) // 2) + raw + '00' * ((-(len(raw) // 2)) % 32))
    offs, pos = [], 32 * len(blobs)
    for b in blobs:
        offs.append(pos)
        pos += len(b) // 2
    return SEL_PROBE + w(32) + w(len(blobs)) + ''.join(w(o) for o in offs) + ''.join(blobs)


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


def cases():
    return [(d, s) for d in DIRECTIONS for s in SIZES]


def probe(block='latest'):
    """WBNB gain (wei) of every (direction, size) in ONE eth_call; 0 = that take would revert."""
    ex = executor()
    cs = cases()
    data = probe_calldata([take_calldata(d, s, 1, ex) for d, s in cs])
    res = rpc('eth_call', call_params(data, None, block)).removeprefix('0x')
    words = [int(res[i:i + 64], 16) for i in range(0, len(res), 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(cs):
        raise RuntimeError('probe: unexpected return length')
    return cs, gains


def gain_of(direction, amount, min_profit, gas_limit=None):
    """Return value of the exact take() as an eth_call; 0 when it reverts."""
    ans = rpc('eth_call', call_params(take_calldata(direction, amount, min_profit, executor()), gas_limit), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def last_take_block(block):
    """Block of the newest Redeemed / Minted log of MDB+ near our send: the winner's block when we lost."""
    logs = rpc('eth_getLogs', [{'address': MDB, 'fromBlock': hex(block - 200), 'toBlock': hex(block + 5),
                                'topics': [[TOPIC_REDEEMED, TOPIC_MINTED]]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(direction, amount, gross, cap, gas_price, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(direction, amount, cap, EXEC), 0, gas_limit, gas_price,
                                max_priority_fee_per_gas=gas_price)
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
    common = dict(hash=tx_hash, direction=direction, amount_wbnb_wei=amount, expected_gross_wei=gross, cap_wei=cap,
                  gas_limit=gas_limit, gas_price_wei=gas_price)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        winner = block if status else last_take_block(block)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        net_wei=(gross - cost) if status else -cost, send_block=block, winner_block=winner,
        tx_index=int(receipt['transactionIndex'], 16), **common)
    return 'won' if status else 'lost'


_memo = {}                         # direction -> (gross that was looked at in full, quiet until)
MEMO_S = 600                       # a standing gain that was not sent is not re-estimated for 10 min unless it grows 10 pct
LOST_QUIET_S = 300                 # after a lost or unknown live send: no new send in that direction for 5 min


def quiet(direction, gross, seconds=MEMO_S):
    _memo[direction] = (gross, time.time() + seconds)


def check():
    """One look: 1 eth_call when nothing is open or the standing gain was already looked at in full.
    Returns True only when a live transaction was sent (the caller then looks again after 3, 10, 30 s)."""
    cs, gains = probe()
    gross = max(gains)
    if gross < MIN_INTEREST_WEI:
        return False
    direction, amount = cs[gains.index(gross)]
    memo = _memo.get(direction)
    if memo and time.time() < memo[1] and gross * 10 <= memo[0] * 11:
        return False
    floor_price = int(rpc('eth_gasPrice', []), 16)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(take_calldata(direction, amount, 1, executor()))), 16)
    except ReadBudgetExceeded:
        raise
    except Exception as e:
        log('simulate_revert', step='estimate', direction=direction, amount_wbnb_wei=amount, gross_wei=gross, error=str(e)[:200])
        quiet(direction, gross)
        return False
    gas_limit = estimate * 5 // 4
    gas_price = max(floor_price, min(GAS_PRICE_MAX_WEI, gross // TIP_SHARE_DEN // gas_limit))
    cap = gas_limit * gas_price                        # the most this send can cost (maxFeePerGas x gasLimit)
    cap_usd = cap / 1e18 * BNB_REF_USD
    log('opportunity', direction=direction, amount_wbnb_wei=amount, gross_wei=gross,
        gains_wei={d + ':' + str(s): g for (d, s), g in zip(cs, gains) if g}, cap_wei=cap, floor_price_wei=floor_price,
        gas_price_wei=gas_price, gas_estimate=estimate, gas_limit=gas_limit, cap_usd=round(cap_usd, 4))
    if gas_price > GAS_PRICE_MAX_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', gas_price_wei=gas_price, gas_limit=gas_limit, cap_usd=cap_usd)
        quiet(direction, gross)
        return False
    if gross * SEND_MULT_DEN <= cap * SEND_MULT_NUM:   # send only when expected gross > 1.3 x this send's cost cap
        log('opportunity_skip', reason='gross_below_send_line', gross_wei=gross, cap_wei=cap)
        quiet(direction, gross)
        return False
    checked, err = gain_of(direction, amount, cap, gas_limit)   # the exact call that would be signed (minProfit = cap)
    if checked <= cap:
        log('simulate_revert', step='guard', direction=direction, amount_wbnb_wei=amount, gross_wei=gross, cap_wei=cap, error=err)
        quiet(direction, gross)
        return False
    if MODE == 'paper':
        # paper sends nothing, so the gain stays: one paper_sim line per 10 min while it stands (or when it grows 10 pct)
        log('paper_sim', result='success', direction=direction, amount_wbnb_wei=amount, gross_wei=checked, cap_wei=cap,
            gas_estimate=estimate, gas_limit=gas_limit, gas_price_wei=gas_price)
        quiet(direction, gross)
        return False
    result = send_live(direction, amount, checked, cap, gas_price, gas_limit)
    if result == 'won':
        _memo.pop(direction, None)
    else:                                              # lost, unknown or refused by the signer: back off, never hammer
        quiet(direction, gross * 1000, LOST_QUIET_S)
    return True


def main():
    """Timer loop with bounded follow-ups. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), mdb=MDB, pair=PAIR_ESHARE_MDB, lender=MOOLAH, sizes=len(SIZES),
        directions=list(DIRECTIONS), poll_seconds=POLL, follow_ups=list(FOLLOW_UPS))
    follow_ups = []
    next_poll = 0
    looks = 0
    while True:
        try:
            now = time.time()
            if follow_ups and now >= follow_ups[0]:
                follow_ups = follow_ups[1:]
                trigger = 'follow_up'
            elif now >= next_poll:
                next_poll = now + POLL
                trigger = 'timer'
            else:
                time.sleep(max(0.5, min([next_poll] + follow_ups[:1]) - now))
                continue
            looks += 1
            sent = check()
            if sent:
                log('look', trigger=trigger, sent=True)
                if trigger != 'follow_up':
                    follow_ups = [time.time() + d for d in FOLLOW_UPS]
            elif looks % 60 == 1:
                log('heartbeat', looks=looks, trigger=trigger)
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
