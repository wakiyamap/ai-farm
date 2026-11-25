#!/usr/bin/env python3
"""Trial: vTokens (vANSEM, vJASPER, ...) minted / redeemed at NAV through the protocol router versus their V3 pools
on HyperEVM.

Each vToken is backed by an ERC-4626 vault priced from HyperCore; anyone can mint it with USDC or redeem it for USDC
through the router, and it also trades on a small vToken/USDC pool. When the pool price is away from the NAV by more
than the fees, one transaction through the TrialVTokenArb executor uses the pool's own flash swap: either the pool
pays vToken, the router redeems it for USDC and the pool is repaid in USDC, or the pool pays USDC, the router mints
the owed vToken with part of it and the pool is repaid in vToken. The executor reverts unless its USDC balance grew
by at least minProfit, so a lost attempt costs gas only.

The NAV moves with HyperCore and has no event, so the bot polls on a timer: one eth_call of the executor's probe()
(all candidates of this poll in one call) every POLL_S seconds.
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

# Route targets: all are call arguments of the executor (registry getters, scratch/trial-vtoken-arb-hyperevm/tokens.py)
USDC = '0xb88339cb7199b77e23db6e890353e22632ba630f'          # HyperEVM USDC, 6 decimals (vault asset)
ROUTER = '0x3de2ba3712035fbabd90803813b2afe9eb1ab2ba'        # protocol router (registry 0xe13ad79d getter 0xa562bdba)
# name: (vToken, pool, vault). Pool = registry 0x988b1fa7(vToken); vault = vToken.backing() -> 0x976a8435().
TOKENS = {
    'vANSEM': ('0xabc475bc4369d6413f7666cc8c52efb001841def', '0x9349bfb0d66e0fc6ca1d53053a143ef078cf41c4', '0xc7f1330ffa5644ed14fbd0ff0efa793669bcce91'),
    'vJASPER': ('0x237325d1dc55d5d17224b60948b174a28879e9c6', '0x73f3a2ad55499acc3578e4d3454277b6994e45c2', '0x4ed285477626288829d2c5b9bb0d97077808a31a'),
    'vFLOOD': ('0xff56312bc817d3db55bfccfe5cad5ab3fabd470f', '0x0a82f8f7a7c554b6d6991a8a40876b96be98a297', '0xa9dee0fb42c54f895d5862de8bf05e63fadf853b'),
    'vSMARTEST': ('0x0c37e0fdbb68403932db2d02ab9fce466aab81d7', '0xd3c35d0649f365a973a8a38605cd88689c71d4ff', '0x6fd4db7d4ef4906e399059dd14ad36fa39b96d7f'),
    'vLUCKYQUAIL': ('0x05553001507b6558f66842c572a57575556f113e', '0xd387cde39b1b2e1b47af568476535e346c5caa9b', '0x5d258fe665ac4d0ec86f1bef2f235de130cc0fb9'),
    'vWINTERMUTE': ('0xa420e38bf9ec09a4ef4d605a6c1a1094bcc04f42', '0x70a8d3081e97dd6eb9736be01cbb6eeac8ac0eff', '0xb3143a2c098df25f37acc7e00a6a2f1c31687952'),
    'vLORACLE': ('0x657bb65fc516f5b102fd4cdbec2135b017f477ef', '0x97f15239248b645214126ca007a1726570508c01', '0x83a6981fc11f411bbf76908b26f8bb7a7a78ef8a'),
    'v2xRTB2': ('0x010a89b07425fb8ec7f124de9d00372174bb6fa4', '0x43291f6494189a5de06d2c34e70176b51c76dc3d', '0x4bcc55e6345f9d0ea5f78c2f8ea31326a6aa7bbf'),
    'vSTEELEAGLE': ('0xe46f39637f9d8177f086d904a68ed1be125e9828', '0xa05132bff160e9324a13105d5998947acfee209c', '0xaeadbea3611da3957ad31f2817aac313a5a684e7'),
    'vRTB2': ('0xc727d544686a9e20f0570a130071f11c135e8dba', '0xbc2af180ff44078c11d7b1815fd70f0bc82718eb', '0xee63de840e391fef9fa607314e95c884088ffa11'),
    'vCEDARSHARK': ('0x75702aaf1b382eab75d7533ea4cbc7209363046d', '0xeadb620d89fcb573ce086e813974fb4cb383f578', '0xc8c8a603097c6034b95147ba2f5267ef03a0a1aa'),
    'vONYXMANTA': ('0x6f566048b35ba3d59d3044b311e8f69b952fc883', '0xa48de6974a237b39e37f9c17ed089b25ba426e04', '0x417981ae931aeff84e372280b982a4d7051ef722'),
    'vGRANDNEBULA': ('0x6b8aea4d4cca07e339c7f10aa0e24b6891422629', '0x709fb5f863c6c29913f11584a1fa0423e5e7eae1', '0x7952e97de05cb8be5657f4a0096f360e6cb39af8'),
    'vMACHI': ('0x2e3b6f396893deac06d82414f648e0659b93ed6f', '0xb9c12707120e0045f976286897b695369b26e22e', '0x7075e29c57c8088d30b09f4f2bd3820cdc771b51'),
    'vCALMPEAK': ('0x76acba3f579142e97e4e69cbb241ef4cb72319f0', '0xf30cfb1349616672b947c68b000a3f1b70f8aabc', '0xc05a5123b73dd95f7ef7897c636cc8325a26235d'),
}
EVERY_POLL = ['vANSEM', 'vJASPER']         # 175 of the 202 incumbent takes in 7 d
ROTATE_N = 2                               # plus this many of the other tokens per poll, in rotation
POOL_WHYPE = '0xbd19e19e4b70eb7f248695a42208bc1edbbfb57d'    # WHYPE/USDT0 0.05%, token0 WHYPE: HYPE price for the gas cap
SEL_RUN = '0xb13c19d9'       # cast sig run((address,address,address,address,address,bool,bool,uint256,uint256,uint256,uint256,uint256,uint256))
SEL_PROBE = '0xb1b279a1'     # cast sig probe((address,address,address,address,address,bool,bool,uint256,uint256,uint256,uint256,uint256,uint256)[])
SEL_SLOT0 = '0x3850c7bd'     # cast sig slot0()
T_REDEEM = '0x1acb8e725301a7601d2e44b94e3cad9274ffd61d95ce257570c128d4b2c5d2be'   # router redeem event (topic0 from receipts)
T_MINT = '0xf60945982f79c9cab3a44143350c7546774426e21d7e50ad46cc065e4e5b1182'     # router mint event (topic0 from receipts)

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
GAS_LIMIT_FALLBACK = 1_300_000  # used only if eth_estimateGas fails (paper); live never sends without an estimate
GAS_MARGIN = 1.15              # fork success used 588k gas (estimate 735k); incumbent takes use 0.8M-0.95M
MAX_FEE_WEI = 3 * 10**9        # hard ceiling on maxFeePerGas: 1.9M x 3 gwei = 0.0057 HYPE
SEND_CAP_USD = 0.95            # the gas cap valued at the pool HYPE price x 1.15 must stay under this
HYPE_MARGIN = 1.15
BID_SHARE = 0.05               # priority fee bid is at most 5% of simulated gross (the incumbent does not bid)
BASE_FEE_MULT = 1.2            # maxFeePerGas = base fee x this + bid
GAIN_OVER_CAP = 1.0            # send only if the simulated gain is above this send's gas cap (trial rule)
MIN_GAIN_UNITS = 10_000        # 0.01 USDC: smaller probe gains are not evaluated at all
AMOUNT_CAP = 40 * 10**6        # USDC cap of one swap; the price band stops it earlier
BANDS = [3_000, 10_000, 30_000]  # ppm of price the swap may move the pool: 3 candidates per token and direction
MARGIN_PPM = 1_000             # mint side: USDC spent on minting above the quoted cost of the owed vToken
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
    """Route = static tuple of 13 words: pool, asset, vToken, router, vault, mint, sync, amount, bandPpm, marginPpm,
    minProfit, maxGasPrice, deadline."""
    return (aw(c['pool']) + aw(USDC) + aw(c['vtoken']) + aw(ROUTER) + aw(c['vault']) + word(1 if c['mint'] else 0) + word(1)
            + word(AMOUNT_CAP) + word(c['band']) + word(MARGIN_PPM) + word(min_profit) + word(max_gas_price) + word(deadline))


def run_data(c, min_profit, max_gas_price, deadline):
    return SEL_RUN + route_words(c, min_profit, max_gas_price, deadline)


def probe_data(cands, deadline):
    body = ''.join(route_words(c, 1, MAX_FEE_WEI, deadline) for c in cands)
    return SEL_PROBE + word(32) + word(len(cands)) + body


def cands_of(name):
    v, pool, vault = TOKENS[name]
    return [{'name': f'{name}:{"mint" if m else "redeem"}:{b}', 'token': name, 'vtoken': v, 'pool': pool, 'vault': vault,
             'mint': m, 'band': b} for m in (True, False) for b in BANDS]


OTHERS = [n for n in TOKENS if n not in EVERY_POLL]


def poll_cands(n):
    """vANSEM and vJASPER every poll; the other 13 tokens two per poll in rotation (each about every 3 min)."""
    names = list(EVERY_POLL)
    for k in range(ROTATE_N):
        names.append(OTHERS[(n * ROTATE_N + k) % len(OTHERS)])
    out = []
    for x in names:
        out += cands_of(x)
    return out


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


def probe(cands, deadline):
    """One eth_call: the USDC gain (6 dp) of every candidate against the same state; 0 = it would revert."""
    frm, ex, ov = ctx()
    res = rpc('eth_call', [{'from': frm, 'to': ex, 'data': probe_data(cands, deadline), 'gas': hex(30_000_000)}, 'latest'] + ov)
    h = res[2:]
    n = int(h[64:128], 16)
    if n != len(cands):
        raise RuntimeError('probe returned a wrong length')
    return [int(h[128 + 64 * i:192 + 64 * i], 16) for i in range(n)]


def hype_usd():
    sq = int(rpc('eth_call', [{'to': POOL_WHYPE, 'data': SEL_SLOT0}, 'latest'])[2:66], 16)
    return (sq / 2**96) ** 2 * 1e12        # USDT0 (6 dp) per WHYPE (18 dp)


def winner_block(vtoken, send_block, exec_addr):
    """Nearest block around our send where someone else minted or redeemed this vToken at the router."""
    logs = rpc('eth_getLogs', [{'address': ROUTER, 'fromBlock': hex(max(0, send_block - 120)),
                               'toBlock': hex(send_block + 5), 'topics': [[T_REDEEM, T_MINT], '0x' + aw(vtoken)]}])
    best = None
    for x in logs:
        if len(x['topics']) > 2 and '0x' + x['topics'][2][-40:].lower() == exec_addr.lower():
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
        other = winner_block(c['vtoken'], b, EXEC)
    except Exception:
        other = None
    log('send_result', hash=h, result='won' if status else 'lost', gas_used=used,
        gas_cost_wei=used * int(receipt['effectiveGasPrice'], 16), send_block=b, winner_block=other,
        blocks_after_winner=(b - other if other is not None else None), simulated_gain_usdc=gain / 1e6,
        candidate=c['name'])


def evaluate(cands, profits):
    """Take the best candidate; send (live) or log (paper) only if its gross exceeds this send's gas cap."""
    i = max(range(len(profits)), key=lambda k: profits[k])
    gain = profits[i]
    if gain == 0:
        return False
    c = cands[i]
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
    max_fee = min(MAX_FEE_WEI, int(base_fee * BASE_FEE_MULT) + priority)
    priority = min(priority, max_fee)
    gas_cap_usd = gas_limit * max_fee / 1e18 * price
    reason = None
    if max_fee < base_fee:
        reason = 'base_fee_above_fee_cap'
    elif gas_cap_usd >= SEND_CAP_USD:
        reason = 'gas_cap_over_usd_limit'
    elif gross_usd <= gas_cap_usd * GAIN_OVER_CAP:
        reason = 'gross_under_gas_cap'
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
        profits={x['name']: p / 1e6 for x, p in zip(cands, profits) if p})
    if MODE == 'live':
        send_live(c, data, gas_limit, max_fee, priority, gain)
    else:
        log('paper_sim', result='success', candidate=c['name'], gain_usdc=gain / 1e6, gas_cap_usd=gas_cap_usd)
    return True


def main():
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, poll_s=POLL_S, bands=BANDS,
        tokens=list(TOKENS), cu_cap=CU_CAP)
    n = 0
    while True:
        try:
            cands = poll_cands(n)
            profits = probe(cands, int(time.time()) + 60)
            n += 1
            if n % 40 == 1:                                   # heartbeat about every 18 min
                log('poll', n=n, best_usdc=max(profits) / 1e6)
            if max(profits) >= MIN_GAIN_UNITS and evaluate(cands, profits):
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
