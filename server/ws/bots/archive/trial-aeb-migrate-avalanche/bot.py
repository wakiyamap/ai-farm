#!/usr/bin/env python3
"""trial: old Avalanche bridge tokens (2020 "AEB" USDT, DAI, ETH, WBTC, LINK, AAVE) against their .e successors.
Every .e BridgeToken has a public swap(oldToken, amount): it burns the old token and mints the .e token 1:1 (up to
swapSupply). The old tokens still sit in V2 pools against WAVAX; when AVAX falls below an old pool's price, one
transaction through the MigrateArb executor does: V2 flash swap of WAVAX out of the .e pair -> sell WAVAX for the old
token on the old pair -> migrate 1:1 -> pay the .e pair -> unwrap the rest to the bot wallet. The executor reverts
unless the wallet is paid at least minProfit. Timer bot: ONE Multicall3 eth_call of all reserves every POLL seconds,
exact V2 integer math off-chain, a probe() eth_call only when the math shows a gain."""
import sys
sys.path.append('/opt/farm/lib')
import datetime
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', 'http://127.0.0.1:8545').rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'avalanche'

WAVAX = '0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7'       # token of every pair below (token0()/token1() read on chain)
MULTICALL3 = '0xca11bde05977b3631167028862be2a173976ca11'  # aggregate3; selftest checks it answers
# name: (old token, .e token, [(old pair, fee per 1000)], [(.e pair, fee per 1000)])
# Old / new tokens: USDT and DAI from the incumbents' receipts, the others accepted because symbol() answers and
# new.swapSupply(old) > 0 (only the bridge role can register a swap token). Pairs: getPair(token, WAVAX) of the four
# factories read from factory() of pairs in the incumbents' receipts (scratch/r6667/aeb_state.py, aeb-state.json);
# old pairs with >= 80 WAVAX, .e pairs with >= 300 WAVAX at 2026-11-21 15:51Z. All four are 0.3 pct V2 forks; a wrong
# fee only makes the take revert in eth_call (never sent).
TOKENS = {
    'USDT': ('0xde3a24028580884448a5397872046a019649b084', '0xc7198437980c041c805a1edcba50c1ce5db95118',
             [('0xe64bfae83ba234ab85bcef5b7a92427e29b3aa11', 997), ('0x9ee0a4e21bd333a6bb2ab298194320b8daa26516', 997),
              ('0xe4b9865c0866346ba3613ec122040a365637fb46', 997)],
             [('0xed8cbd9f0ce3c6986b22002f03c6475ceb7a6256', 997), ('0xe28984e1ee8d431346d32bec9ec800efb643eef4', 997)]),
    'DAI': ('0xba7deebbfc5fa1100fb055a87773e1e99cd3507a', '0xd586e7f844cea2f87f50152665bcbc2c279d8d70',
            [('0x17a2e8275792b4616befb02eb9ae699aa0dcb94b', 997)],
            [('0xba09679ab223c6bdaf44d45ba2d7279959289ab0', 997), ('0x87dee1cc9ffd464b79e058ba20387c1984aed86a', 997)]),
    'ETH': ('0xf20d962a6c8f70c731bd838a3a388d7d48fa6e15', '0x49d5c2bdffac6ce2bfdb6640f4f80f226bc10bab',
            [('0x1acf1583bebdca21c8025e172d8e8f2817343d65', 997), ('0x083e14c8c0e122e374e4c6ff2169d8db7e6728be', 997)],
            [('0xfe15c2695f1f920da45c30aae47d11de51007af9', 997), ('0x7c05d54fc5cb6e4ad87c6f5db3b807c94bb89c52', 997)]),
    'WBTC': ('0x408d4cd0adb7cebd1f1a1c33a0ba2098e1295bab', '0x50b7545627a5162f82a992c33b87adc75187b218',
             [('0x7a6131110b82dacbb5872c7d352bfe071ea6a17c', 997)],
             [('0xd5a37dc5c9a396a03dd1136fc76a1a02b1c88ffa', 997), ('0x5764b8d8039c6e32f1e5d8de8da05ddf974ef5d3', 997)]),
    'LINK': ('0xb3fe5374f67d7a22886a0ee082b2e2f9d2651651', '0x5947bb275c521040051d82396192181b413227a3',
             [('0xbbc7fff833d27264aac8806389e02f717a5506c9', 997)],
             [('0x6f3a0c89f611ef5dc9d96650324ac633d02265d3', 997), ('0x5875c368cddd5fb9bf2f410666ca5aad236dabd4', 997)]),
    'AAVE': ('0x8ce2dee54bb9921a2ae0a63dbb2df8ed88b91dd9', '0x63a72806098bd3d9520cc43356dd78afe5d386d9',
             [('0x5f233a14e1315955f48c5750083d9a44b0df8b50', 997)],
             [('0xc3e6d9f7a3a5e3e223356383c7c055ee3f26a34f', 997), ('0x5944f135e4f1e3fa2e5550d4b5170783868cc4fe', 997)]),
}
USD_PAIR = '0xed8cbd9f0ce3c6986b22002f03c6475ceb7a6256'    # Trader Joe WAVAX / USDT.e: AVAX price for the USD cap only

# Selectors, all from `cast sig` (scratch/trial-aeb-migrate-avalanche/setup.sh).
SEL_TAKE = '0xfc5174a9'         # take((address,address,address,address,address,uint256,uint256,uint256,uint256))
SEL_PROBE = '0xf0f93470'        # probe((address,address,address,address,address,uint256,uint256,uint256,uint256)[])
SEL_RESERVES = '0x0902f1ac'     # getReserves()
SEL_TOKEN0 = '0x0dfe1681'       # token0()
SEL_SWAPSUPPLY = '0xab32dbb7'   # swapSupply(address)
SEL_AGG3 = '0x82ad56cb'         # aggregate3((address,bool,bytes)[])
TOPIC_SWAP = '0x562c219552544ec4c9d7a8eb850f80ea152973e315372bf4999fe7c953ea004f'   # .e token Swap event (from a receipt)

PAPER_EXEC = '0x00000000000000000000000000000000000f11a8'   # code-override address, paper only
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000321'  # owner baked into the fork deployment's runtime code
EXEC = os.environ.get('EXECUTOR_ADDR_AVALANCHE') or os.environ.get('EXECUTOR_ADDR')
if MODE == 'live' and not EXEC:
    raise SystemExit('EXECUTOR_ADDR_AVALANCHE or EXECUTOR_ADDR required in live mode')
RUNTIME_FILE = HERE / 'executor-runtime.hex'

POLL = 40                          # seconds between looks (one eth_call each)
MIN_INTEREST_WEI = 2 * 10**15      # 0.002 AVAX: below this no take covers its gas
SEND_MULT_NUM, SEND_MULT_DEN = 13, 10   # send when gross > 1.3 x the send's gas cap (incumbents wait for about 3-4 x their gas)
TIP_SHARE_DEN = 10                 # priority fee: at most 1/10 of gross spread over the gas limit ...
TIP_MAX_WEI = 3 * 10**9            # ... and never above 3 gwei
TIP_MIN_WEI = 10**9
MAX_FEE_CAP_WEI = 60 * 10**9       # never sign above 60 gwei
GAS_LIMIT_MAX = 600_000
AVAX_REF_MULT = 1.15               # USD cap uses the pool price x 1.15
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


def w(n):
    return format(n, '064x')


def a(addr):
    return addr.lower().removeprefix('0x').zfill(64)


# ---- reads: every reserve and swap supply in one Multicall3 eth_call ----
def all_pairs():
    seen = []
    for old, new, olds, news in TOKENS.values():
        for p, _ in olds + news:
            if p not in seen:
                seen.append(p)
    if USD_PAIR not in seen:
        seen.append(USD_PAIR)
    return seen


def agg3(calls, block='latest'):
    """aggregate3 with allowFailure = true; returns a list of (success, return bytes hex without 0x)."""
    items = []
    for target, data in calls:
        raw = data.removeprefix('0x')
        items.append(a(target) + w(1) + w(0x60) + w(len(raw) // 2) + raw + '00' * ((-(len(raw) // 2)) % 32))
    offs, pos = [], 32 * len(items)
    for it in items:
        offs.append(pos)
        pos += len(it) // 2
    data = SEL_AGG3 + w(32) + w(len(items)) + ''.join(w(o) for o in offs) + ''.join(items)
    res = rpc('eth_call', [{'to': MULTICALL3, 'data': data}, block]).removeprefix('0x')
    n = int(res[64:128], 16)
    base = 128
    out = []
    for i in range(n):
        off = int(res[base + 64 * i:base + 64 * (i + 1)], 16) * 2 + base
        ok = int(res[off:off + 64], 16) == 1
        ln = int(res[off + 128:off + 192], 16) * 2
        out.append((ok, res[off + 192:off + 192 + ln]))
    if len(out) != len(calls):
        raise RuntimeError('aggregate3: unexpected return length')
    return out


_token0 = {}


def read_state(block='latest'):
    """{'res': {pair: (wavax reserve, token reserve)}, 'supply': {name: swapSupply}}; token0() cached after one read."""
    pairs = all_pairs()
    need0 = [p for p in pairs if p not in _token0]
    calls = [(p, SEL_RESERVES) for p in pairs] + [(new, SEL_SWAPSUPPLY + a(old)) for old, new, _, _ in TOKENS.values()]
    calls += [(p, SEL_TOKEN0) for p in need0]
    out = agg3(calls, block)
    k = len(pairs) + len(TOKENS)
    for p, (ok, ret) in zip(need0, out[k:]):
        if ok and len(ret) >= 64:
            _token0[p] = '0x' + ret[24:64]
    res = {}
    for p, (ok, ret) in zip(pairs, out[:len(pairs)]):
        if not ok or len(ret) < 128 or p not in _token0:
            continue
        r0, r1 = int(ret[:64], 16), int(ret[64:128], 16)
        res[p] = (r0, r1) if _token0[p] == WAVAX else (r1, r0)
    supply = {}
    for name, (ok, ret) in zip(TOKENS, out[len(pairs):k]):
        supply[name] = int(ret[:64], 16) if ok and len(ret) >= 64 else 0
    return {'res': res, 'supply': supply}


# ---- exact V2 math ----
def amount_out(x, rin, rout, fee):
    return x * fee * rout // (rin * 1000 + x * fee)


def plan(rwo, rto, fo, rwn, rtn, fn, supply):
    """Best WAVAX amount to sell into the old pair: (gain, sellIn, oldOut, borrow). Ternary search on exact math."""
    def gain(x):
        u = amount_out(x, rwo, rto, fo)
        if u > supply or u >= rtn:
            return -1
        return amount_out(u, rtn, rwn, fn) - x
    lo, hi = 0, rwo // 3
    for _ in range(64):
        m1 = lo + (hi - lo) // 3
        m2 = hi - (hi - lo) // 3
        if gain(m1) < gain(m2):
            lo = m1
        else:
            hi = m2
    x = (lo + hi) // 2
    g = gain(x)
    if g <= 0:
        return 0, 0, 0, 0
    u = amount_out(x, rwo, rto, fo)
    return g, x, u, amount_out(u, rtn, rwn, fn)


def candidates(state):
    """Every (token, old pair, .e pair) with a positive calculated gain, best first."""
    out = []
    for name, (old, new, olds, news) in TOKENS.items():
        sup = state['supply'].get(name, 0)
        for po, fo in olds:
            for pn, fn in news:
                if po not in state['res'] or pn not in state['res']:
                    continue
                rwo, rto = state['res'][po]
                rwn, rtn = state['res'][pn]
                if min(rwo, rto, rwn, rtn) == 0:
                    continue
                g, x, u, borrow = plan(rwo, rto, fo, rwn, rtn, fn, sup)
                if g > 0:
                    out.append({'token': name, 'pairNew': pn, 'pairOld': po, 'old': old, 'new': new,
                                'borrow': borrow, 'sellIn': x, 'oldOut': u, 'calc_gain': g})
    out.sort(key=lambda c: -c['calc_gain'])
    return out


def take_words(c, min_profit):
    return (a(WAVAX) + a(c['pairNew']) + a(c['pairOld']) + a(c['old']) + a(c['new'])
            + w(c['borrow']) + w(c['sellIn']) + w(c['oldOut']) + w(min_profit))


def take_calldata(c, min_profit):
    return SEL_TAKE + take_words(c, min_profit)


def probe_calldata(cands):
    return SEL_PROBE + w(32) + w(len(cands)) + ''.join(take_words(c, 1) for c in cands)


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


def probe(cands, block='latest'):
    """Gains (wei of WAVAX) of the candidates on chain in ONE eth_call; 0 = that take would revert."""
    res = rpc('eth_call', call_params(probe_calldata(cands), None, block)).removeprefix('0x')
    words = [int(res[i:i + 64], 16) for i in range(0, len(res), 64)]
    gains = words[2:2 + words[1]]
    if len(gains) != len(cands):
        raise RuntimeError('probe: unexpected return length')
    return gains


def gain_of(c, min_profit, gas_limit=None):
    """Return value of the exact take() as an eth_call; 0 when it reverts."""
    ans = rpc('eth_call', call_params(take_calldata(c, min_profit), gas_limit), raw=True)
    if 'error' in ans:
        return 0, str(ans['error'])[:160]
    return int(ans['result'], 16), None


def last_migration_block(block):
    """Block of the newest .e Swap (migration) event near our send: the winner's block when we lost."""
    news = [new for _, new, _, _ in TOKENS.values()]
    logs = rpc('eth_getLogs', [{'address': news, 'fromBlock': hex(block - 60), 'toBlock': hex(block + 5), 'topics': [TOPIC_SWAP]}])
    return max((int(x['blockNumber'], 16) for x in logs), default=None)


def send_live(c, gross, cap, max_fee, tip, gas_limit):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, take_calldata(c, cap), 0, gas_limit, max_fee, max_priority_fee_per_gas=tip)
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
    common = dict(hash=tx_hash, token=c['token'], pair_old=c['pairOld'], pair_new=c['pairNew'], sell_in_wei=c['sellIn'],
                  expected_gross_wei=gross, cap_wei=cap, gas_limit=gas_limit, max_fee_wei=max_fee, tip_wei=tip)
    if not receipt:
        log('send_result', result='unknown', gas_used=None, winner_block=None, **common)
        return
    block = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        winner = block if status else last_migration_block(block)
    except Exception as e:
        log('winner_lookup_error', hash=tx_hash, error=str(e)[:160])
        winner = None
    log('send_result', result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        net_wei=(gross - cost) if status else -cost, send_block=block, winner_block=winner,
        tx_index=int(receipt['transactionIndex'], 16), **common)


def check():
    """One look: 1 eth_call when nothing is open. Returns True when a gain above MIN_INTEREST was seen."""
    state = read_state()
    cands = [c for c in candidates(state) if c['calc_gain'] >= MIN_INTEREST_WEI][:4]
    if not cands:
        return False
    gains = probe(cands)
    gross = max(gains)
    c = cands[gains.index(gross)]
    if gross < MIN_INTEREST_WEI:
        log('check', result='calc_gain_not_on_chain', token=c['token'], calc_gain_wei=c['calc_gain'], chain_gain_wei=gross)
        return False
    base_fee = int(rpc('eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    try:
        estimate = int(rpc('eth_estimateGas', call_params(take_calldata(c, 1))), 16)
    except Exception as e:
        log('simulate_revert', step='estimate', token=c['token'], gross_wei=gross, error=str(e)[:200])
        return True
    gas_limit = estimate * 11 // 10                # the estimate already sits about 25 pct above the gas used (fork)
    tip = max(TIP_MIN_WEI, min(TIP_MAX_WEI, gross // TIP_SHARE_DEN // gas_limit))
    max_fee = base_fee + base_fee // 8 + tip
    cap = gas_limit * max_fee                     # the most this send can cost
    usd_res = state['res'].get(USD_PAIR)
    avax_usd = (usd_res[1] / 1e6) / (usd_res[0] / 1e18) * AVAX_REF_MULT if usd_res else 100.0
    cap_usd = cap / 1e18 * avax_usd
    log('opportunity', token=c['token'], pair_old=c['pairOld'], pair_new=c['pairNew'], sell_in_wei=c['sellIn'],
        gross_wei=gross, calc_gain_wei=c['calc_gain'], cap_wei=cap, base_fee=base_fee, tip_wei=tip, max_fee_wei=max_fee,
        gas_estimate=estimate, gas_limit=gas_limit, cap_usd=round(cap_usd, 4))
    if max_fee > MAX_FEE_CAP_WEI or gas_limit > GAS_LIMIT_MAX or cap_usd >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', token=c['token'], max_fee_wei=max_fee, gas_limit=gas_limit, cap_usd=cap_usd)
        return True
    if gross * SEND_MULT_DEN <= cap * SEND_MULT_NUM:   # send only when expected gross > 1.3 x this send's gas cap
        log('opportunity_skip', reason='gross_below_send_line', token=c['token'], gross_wei=gross, cap_wei=cap)
        return True
    checked, err = gain_of(c, cap, gas_limit)      # the exact call that would be signed (minProfit = gas cap)
    if checked <= cap:
        log('simulate_revert', step='guard', token=c['token'], gross_wei=gross, cap_wei=cap, error=err)
        return True
    if MODE == 'paper':
        log('paper_sim', result='success', token=c['token'], pair_old=c['pairOld'], pair_new=c['pairNew'],
            sell_in_wei=c['sellIn'], gross_wei=checked, cap_wei=cap, gas_estimate=estimate, gas_limit=gas_limit,
            max_fee_wei=max_fee, tip_wei=tip)
    else:
        send_live(c, checked, cap, max_fee, tip, gas_limit)
    return True


def main():
    """Timer loop. Every relay read is inside the try that catches the bot's CU cap."""
    if MODE == 'paper' and not RUNTIME_FILE.exists():
        raise SystemExit('missing executor-runtime.hex (paper code override)')
    log('start', mode=MODE, executor=executor(), tokens=list(TOKENS), pairs=len(all_pairs()), poll_seconds=POLL)
    next_poll = 0
    looks = 0
    while True:
        try:
            now = time.time()
            if now >= next_poll:
                next_poll = now + POLL
                seen = check()
                looks += 1
                if looks % 90 == 1 and not seen:
                    log('heartbeat', looks=looks)
                if seen and MODE == 'live':
                    next_poll = time.time() + 8    # part of the gap may be left, or the send lost: look again soon
            else:
                time.sleep(max(0.5, next_poll - now))
        except ReadBudgetExceeded as e:
            log('read_budget', error=str(e))
            now = datetime.datetime.now(datetime.timezone.utc)
            time.sleep(86400 - (now.hour * 3600 + now.minute * 60 + now.second) + 5)   # to 00:00 UTC
        except Exception as e:
            log('loop_error', error=str(e)[:250])
            next_poll = time.time() + POLL
            time.sleep(5)


if __name__ == '__main__':
    main()
