#!/usr/bin/env python3
"""trial-mayan-redeem-arbitrum: deliver Mayan CCTP bridge messages (MayanCircle.redeemWithFee) on Arbitrum for the redeem fee.

A user bridges USDC with MayanCircle.bridgeWithFee on a source chain (Base, Ethereum) and sets redeemFee, paid on the
destination to whoever delivers the CCTP message, Circle's attestation and the Wormhole VAA. The source transaction is
public about 15-20 minutes before both attestations exist (CCTP standard finality), so the bot prepares the call in
advance, polls Circle's iris API and Wormholescan when the attestations are due, and sends one executor call the moment
both are there. Paper mode simulates the same call with a code override and sends nothing.
"""
import base64
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.append('/opt/farm/lib')   # farmbot_signer (live only)

HERE = Path(__file__).resolve().parent
MODE = os.environ.get('BOT_MODE', 'paper')
RELAY = os.environ.get('RPC_RELAY_URL', '').rstrip('/')
LANE = os.environ.get('RPC_LANE', 'paper')
CHAIN = 'arbitrum'
EXEC = os.environ.get('EXECUTOR_ADDR_ARBITRUM') or os.environ.get('EXECUTOR_ADDR')
PAPER_OWNER = '0xc0ffee0000000000000000000000000000000001'   # owner baked into the fork deployment's runtime code
PAPER_EXEC = '0x00000000000000000000000000000000000ec0de'    # paper only: address the code override is placed at
RUNTIME = (HERE / 'executor-runtime.hex').read_text().strip() if MODE != 'live' else None

CIRCLE = '0x875d6d37ec55c8cf220b9e5080717549d8aa8eca'   # MayanCircle, same address on every chain (verified source)
FEEMGR = '0x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523'   # MayanCircle.feeManager() on arbitrum
USDC = '0xaf88d065e77c8cc2239327c5edb3a432268e5831'     # native USDC on arbitrum, 6 decimals
WETH_USDC = '0xc6962004f452be9203591991d15f6b388e09e8d0'  # Uniswap V3 WETH/USDC 0.05 pct (token0 WETH, token1 USDC), price only
DEST_DOMAIN = 3                                         # CCTP domain of arbitrum (MayanCircle.localDomain())
# source chains: relay name -> wormhole chain id, CCTP domain, Wormhole core (MayanCircle.wormhole() there), seconds from
# the source block to the first poll (redeems in the last 7 d landed 999-1,379 s after a Base source block and
# 886-1,155 s after an Ethereum one)
SOURCES = {
    'base': {'wh': 30, 'domain': 6, 'core': '0xbebdb6c8ddc678ffa9f8748f85c815c556dd8ac6', 'first_poll_s': 780, 'lookback_blocks': 7500},
    'ethereum': {'wh': 2, 'domain': 0, 'core': '0x98f3c9e6e3face36baad05fe09d375ef1464288b', 'first_poll_s': 720, 'lookback_blocks': 125},
}
T_LMP = '0x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2'   # cast keccak LogMessagePublished(address,uint64,uint32,bytes,uint8)
T_MS = '0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036'    # cast keccak MessageSent(bytes)
T_FEE = '0x652893d29fd820a4f183b65e6138f2125655352c510e215ab9202d37bd46a4d1'   # cast keccak FeeDeposited(address,address,uint256)
SEL_BRIDGE = '2072197f'    # cast sig bridgeWithFee(address,uint256,uint64,uint64,bytes32,uint32,uint8,bytes)
SEL_RUN = '0x2ce322f8'     # cast sig run(address,address,address,bytes,bytes,bytes,(uint8,bytes32,uint64,uint64,uint64,bytes32,bytes32),uint256)
SEL_SLOT0 = '0x3850c7bd'   # cast sig slot0()
IRIS = 'https://iris-api.circle.com/v1/messages/{domain}/{tx}'
WHSCAN = 'https://api.wormholescan.io/api/v1/vaas/{wh}/{emitter}/{seq}'
EMITTER = '0' * 24 + CIRCLE[2:]

LOG = HERE / 'logs' / 'bot.jsonl'
STATE = HERE / 'state' / 'state.json'
CU_FILE = HERE / 'state' / 'cu.json'
LOG.parent.mkdir(exist_ok=True)
STATE.parent.mkdir(exist_ok=True)

# ---- loss guard -----------------------------------------------------------------------------
ETH_USD_MIN, ETH_USD_MAX = 300.0, 20000.0   # a pool price outside this band is treated as unreadable: no send
ETH_REF_USD = 4000.0           # deliberately high reference price for the signed-cap check (ETH is about 1,700)
MAX_TX_USD = 0.90              # signed gas cap (maxFeePerGas x gasLimit) at ETH_REF_USD stays under this
MAX_FEE_WEI = 500_000_000      # 0.5 gwei absolute ceiling for maxFeePerGas (arbitrum base fee is 0.02 gwei)
MAX_GAS_LIMIT = 1_500_000      # fork: 426,937 used; estimate 475,137
SIM_GAS = 1_500_000
GAS_MARGIN_NUM, GAS_MARGIN_DEN = 12, 10    # gas limit = eth_estimateGas x 1.20 (Nitro: the estimate includes the L1 part)
BASE_FEE_HEADROOM_PCT = 30     # maxFeePerGas = latest base fee x 1.30 + tip
TIP_WEI = 1_000_000            # 0.001 gwei; arbitrum orders first come first served, a tip buys nothing; never 0
MIN_FEE_USDC = 20_000          # 0.02 USDC: below one attempt's gas (about 0.02 USD) nothing is prepared
MAX_FEE_USDC = 400_000_000     # sanity bound on a decoded redeemFee
SCAN_INTERVAL = 300            # source log scan per source chain
HOT_POLL = 3                   # seconds between attestation polls while a message is due
HOT_WINDOW = 1800              # after first_poll_s: poll every HOT_POLL for this long, then every COLD_POLL
COLD_POLL = 300
DROP_AFTER = 3 * 86400         # a message nobody delivered is retried for 3 days
RESULT_CHECKS = (120, 600, 3600)   # paper: seconds after 'ready' at which the winner is looked up
RELAY_CU_CAP = 95_000          # per UTC day, all chains
CU_COST = {'eth_call': 26, 'eth_estimateGas': 20, 'eth_getLogs': 75, 'eth_getTransactionReceipt': 20,
           'eth_blockNumber': 10, 'eth_getBlockByNumber': 20, 'eth_getBalance': 20, 'eth_getTransactionByHash': 20}
_id = 0
_http_err = {}


class ReadBudgetExceeded(Exception):
    pass


def log(ev, **kw):
    row = {'ts': round(time.time(), 3), 'ev': ev, **kw}
    with LOG.open('a') as f:
        f.write(json.dumps(row, separators=(',', ':'), default=str) + '\n')


def rpc(chain, method, params):
    global _id
    day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    try:
        budget = json.loads(CU_FILE.read_text())
    except Exception:
        budget = {'day': day, 'cu': 0}
    if budget.get('day') != day:
        budget = {'day': day, 'cu': 0}
    cost = CU_COST.get(method, 26)
    if budget['cu'] + cost > RELAY_CU_CAP:
        raise ReadBudgetExceeded(f'{RELAY_CU_CAP} relay CU/day bot cap reached')
    budget['cu'] += cost
    CU_FILE.write_text(json.dumps(budget))
    _id += 1
    body = json.dumps({'jsonrpc': '2.0', 'id': _id, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(f'{RELAY}/{chain}?lane={LANE}', body, {'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ans = json.load(resp)
    if 'error' in ans:
        raise RuntimeError(f'{method}: {str(ans["error"])[:300]}')
    return ans['result']


def http_json(url, host):
    """GET a public attestation API. Returns the JSON, or None on 404 / error (logged at most once a minute per host)."""
    try:
        req = urllib.request.Request(url, headers={'accept': 'application/json', 'user-agent': 'relay-bot/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        err = f'http_{e.code}'
    except Exception as e:
        err = repr(e)[:160]
    now = time.time()
    if now - _http_err.get(host, 0) > 60:
        _http_err[host] = now
        log('http_error', host=host, error=err)
    return None


def word(n):
    return format(n, '064x')


def aword(a):
    return a.lower().removeprefix('0x').zfill(64)


def enc_bytes(hexstr):
    raw = hexstr.removeprefix('0x')
    n = len(raw) // 2
    return word(n) + raw + '0' * ((64 - len(raw) % 64) % 64)


def run_calldata(cctp, sigs, vaa, p, min_profit):
    """ABI encoding of run(circle, feeManager, token, bytes cctpMsg, bytes cctpSigs, bytes encodedVm,
    (uint8 payloadType, bytes32 destAddr, uint64 gasDrop, uint64 redeemFee, uint64 burnAmount, bytes32 burnToken,
    bytes32 customPayload), uint256 minProfit): 14 head words, then the three byte strings (checked against cast)."""
    t1, t2, t3 = enc_bytes(cctp), enc_bytes(sigs), enc_bytes(vaa)
    o1 = 14 * 32
    o2 = o1 + len(t1) // 2
    o3 = o2 + len(t2) // 2
    head = (aword(CIRCLE) + aword(FEEMGR) + aword(USDC) + word(o1) + word(o2) + word(o3)
            + word(p['payloadType']) + p['destAddr'] + word(p['gasDrop']) + word(p['redeemFee']) + word(p['burnAmount'])
            + p['burnToken'] + p['customPayload'] + word(min_profit))
    return SEL_RUN + head + t1 + t2 + t3


def bot_address():
    import farmbot_signer
    a = farmbot_signer.my_address()
    a = a.get('address') if isinstance(a, dict) else a   # my_address() returns {"ok":..., "address":...}
    if not isinstance(a, str) or len(a) != 42:
        raise RuntimeError('signer my_address returned no address')
    return a


def exec_ctx():
    if MODE == 'live':
        return bot_address(), EXEC, None
    return PAPER_OWNER, PAPER_EXEC, {PAPER_EXEC: {'code': RUNTIME}}


def eth_usd():
    """USDC per WETH from slot0 of the Uniswap V3 WETH/USDC pool (token0 WETH 18 dec, token1 USDC 6 dec)."""
    raw = rpc(CHAIN, 'eth_call', [{'to': WETH_USDC, 'data': SEL_SLOT0}, 'latest'])
    sqrt_p = int(raw[2:66], 16)
    price = sqrt_p * sqrt_p * 10**12 / 2**192
    if not ETH_USD_MIN < price < ETH_USD_MAX:
        raise RuntimeError(f'ETH/USD {price} outside the plausible band')
    return price


# ---- source side: find bridgeWithFee messages bound for arbitrum ---------------------------------

def decode_bridge(inp_hex, cctp):
    """Find bridgeWithFee(tokenIn, amountIn, redeemFee, gasDrop, destAddr, destDomain, payloadType, customPayload) anywhere
    in the source transaction's input (Mayan's forwarder nests it) and cross-check it against the CCTP message."""
    raw = bytes.fromhex(inp_hex.removeprefix('0x'))
    sel = bytes.fromhex(SEL_BRIDGE)
    burn_token = cctp[120:152]
    amount = int.from_bytes(cctp[184:216], 'big')
    i = raw.find(sel)
    while i >= 0:
        a = raw[i + 4:i + 4 + 8 * 32]
        if len(a) == 8 * 32:
            w = [int.from_bytes(a[32 * k:32 * k + 32], 'big') for k in range(8)]
            if (w[0].to_bytes(32, 'big') == burn_token and w[1] == amount and w[5] == DEST_DOMAIN and w[2] < 2**64 and w[3] < 2**64
                    and w[6] < 256):
                return {'payloadType': w[6], 'destAddr': word(w[4]), 'gasDrop': w[3], 'redeemFee': w[2], 'burnAmount': amount,
                        'burnToken': burn_token.hex(), 'customPayload': word(0)}
        i = raw.find(sel, i + 1)
    return None


def scan_source(s, name, now):
    src = SOURCES[name]
    head = int(rpc(name, 'eth_blockNumber', []), 16)
    frm = s['cursor'].get(name)
    frm = head - src['lookback_blocks'] if frm is None else frm + 1
    if frm > head:
        return
    logs = rpc(name, 'eth_getLogs', [{'address': src['core'], 'fromBlock': hex(frm), 'toBlock': hex(head),
                                      'topics': [T_LMP, '0x' + aword(CIRCLE)]}])
    for lg in logs:
        seq = int(lg['data'][2:66], 16)
        key = f'{name}:{seq}'
        if key in s['pending'] or key in s['done']:
            continue
        h = lg['transactionHash']
        receipt = rpc(name, 'eth_getTransactionReceipt', [h])
        cctp = None
        for x in receipt['logs']:
            if x['topics'] and x['topics'][0] == T_MS:
                d = bytes.fromhex(x['data'][2:])
                m = d[64:64 + int.from_bytes(d[32:64], 'big')]
                # CCTP v1 message: version u32 | srcDomain u32 | dstDomain u32 | nonce u64 | sender | recipient | destCaller | body
                # body (from 116): version u32 | burnToken | mintRecipient | amount | messageSender
                if len(m) == 248 and int.from_bytes(m[8:12], 'big') == DEST_DOMAIN and m[152 + 12:184] == bytes.fromhex(CIRCLE[2:]):
                    cctp = m
        if cctp is None:
            s['done'][key] = {'why': 'not_for_arbitrum', 't': now}
            continue
        tx = rpc(name, 'eth_getTransactionByHash', [h])
        p = decode_bridge(tx['input'], cctp)
        blk = rpc(name, 'eth_getBlockByNumber', [lg['blockNumber'], False])
        src_ts = int(blk['timestamp'], 16)
        if p is None:
            s['done'][key] = {'why': 'no_bridgeWithFee_in_input', 't': now}
            log('source_skip', key=key, src_tx=h, reason='no_bridgeWithFee_in_input')
            continue
        reason = None
        if p['payloadType'] != 1:
            reason = 'payload_type_not_1'       # type 2 may only be redeemed by its destination address
        elif p['gasDrop'] != 0:
            reason = 'gas_drop_needs_native'    # the relayer would have to pay native to the user: not taken
        elif not MIN_FEE_USDC <= p['redeemFee'] <= MAX_FEE_USDC:
            reason = 'fee_below_min_or_implausible'
        if reason:
            s['done'][key] = {'why': reason, 't': now, 'fee': p['redeemFee']}
            log('source_skip', key=key, src_tx=h, reason=reason, redeem_fee=p['redeemFee'], gas_drop=p['gasDrop'])
            continue
        s['pending'][key] = {'src': name, 'seq': seq, 'src_tx': h, 'src_ts': src_ts, 'cctp': '0x' + cctp.hex(), 'p': p,
                             'sigs': None, 'vaa': None, 'ready_ts': None, 'state': 'wait', 'next': src_ts + src['first_poll_s'],
                             'sim_fail': 0, 'checks': 0}
        log('opportunity', key=key, src_tx=h, src_ts=src_ts, redeem_fee_usdc=p['redeemFee'], amount=p['burnAmount'],
            dest=p['destAddr'][-40:], first_poll_ts=src_ts + src['first_poll_s'])
    s['cursor'][name] = head


# ---- destination side ---------------------------------------------------------------------------

def fetch_attestations(it):
    src = SOURCES[it['src']]
    if not it['sigs']:
        j = http_json(IRIS.format(domain=src['domain'], tx=it['src_tx']), 'iris')
        for m in (j or {}).get('messages', []) or []:
            att = m.get('attestation') or ''
            if (m.get('message') or '').lower() == it['cctp'] and att.startswith('0x') and len(att) > 100:
                it['sigs'] = att
    if not it['vaa']:
        j = http_json(WHSCAN.format(wh=src['wh'], emitter=EMITTER, seq=it['seq']), 'wormholescan')
        v = ((j or {}).get('data') or {}).get('vaa')
        if v:
            it['vaa'] = '0x' + base64.b64decode(v).hex()
    return bool(it['sigs'] and it['vaa'])


def winner(it, from_block):
    """The FeeDeposited of this message's fee on the fee manager: (block, tx, relayer, block timestamp) or None."""
    logs = rpc(CHAIN, 'eth_getLogs', [{'address': FEEMGR, 'fromBlock': hex(from_block), 'toBlock': 'latest', 'topics': [T_FEE]}])
    for lg in logs:
        d = lg['data'][2:]
        if int(d[128:192], 16) == it['p']['redeemFee'] and d[64 + 24:128] == USDC[2:]:
            rc = rpc(CHAIN, 'eth_getTransactionReceipt', [lg['transactionHash']])
            # the same transaction must pay this message's recipient (USDC Transfer to destAddr)
            dest = it['p']['destAddr']
            if any(len(x['topics']) == 3 and x['topics'][2][2:] == dest for x in rc['logs']):
                blk = rpc(CHAIN, 'eth_getBlockByNumber', [lg['blockNumber'], False])
                return int(lg['blockNumber'], 16), lg['transactionHash'], '0x' + d[24:64], int(blk['timestamp'], 16)
    return None


def send_live(key, it, data, gas_limit, max_fee, fee, cap_wei, price):
    import farmbot_signer
    reply = farmbot_signer.send(CHAIN, EXEC, data, 0, gas_limit, max_fee, max_priority_fee_per_gas=TIP_WEI)
    h = None
    if isinstance(reply, dict):
        h = reply.get('txHash') or reply.get('tx_hash') or reply.get('hash')
    if not h:
        log('signer_reject', reply=reply, key=key)   # final, never retried
        return
    log('send', hash=h, key=key, gas_limit=gas_limit, max_fee=max_fee, priority=TIP_WEI, expected_gross_usdc=fee,
        min_profit_usdc=fee, gas_cap_wei=cap_wei, executor=EXEC)
    receipt = None
    for _ in range(30):
        time.sleep(1)
        try:
            receipt = rpc(CHAIN, 'eth_getTransactionReceipt', [h])
        except ReadBudgetExceeded:
            break
        except Exception:
            receipt = None
        if receipt:
            break
    if not receipt:
        log('send_result', hash=h, key=key, result='unknown', gas_used=None, winner_block=None)
        return
    b = int(receipt['blockNumber'], 16)
    status = int(receipt['status'], 16)
    used = int(receipt['gasUsed'], 16)
    cost = used * int(receipt['effectiveGasPrice'], 16)
    try:
        wn = winner(it, b - 4000)
    except Exception:
        wn = None
    log('send_result', hash=h, key=key, result='won' if status else 'lost', gas_used=used, gas_cost_wei=cost,
        gas_cost_usd=round(cost / 1e18 * price, 5), send_block=b, winner_block=wn[0] if wn else None, winner_tx=wn[1] if wn else None,
        winner_relayer=wn[2] if wn else None, blocks_after_winner=(b - wn[0] if wn else None),
        gross_usdc=fee if status else 0, net_usd=round((fee / 1e6 if status else 0) - cost / 1e18 * price, 5))


def work_item(s, key, it, ctx, now):
    """One step for a pending message. Returns True when the item is finished."""
    if now - it['src_ts'] > DROP_AFTER:
        log('expired', key=key)
        return True
    src = SOURCES[it['src']]
    hot = now < it['src_ts'] + src['first_poll_s'] + HOT_WINDOW
    if it['state'] == 'watch':      # paper: after the simulated send, look up who delivered it and when
        wn = winner(it, it['ready_block'])
        it['checks'] += 1
        if wn:
            log('paper_outcome', key=key, winner_block=wn[0], winner_tx=wn[1], winner_relayer=wn[2], winner_ts=wn[3],
                ready_ts=it['ready_ts'], seconds_winner_after_ready=wn[3] - int(it['ready_ts']), redeem_fee_usdc=it['p']['redeemFee'])
            return True
        if it['checks'] >= len(RESULT_CHECKS):
            log('paper_outcome', key=key, winner_block=None, note='nobody delivered it within an hour of ready', ready_ts=it['ready_ts'])
            return True
        it['next'] = it['ready_ts'] + RESULT_CHECKS[it['checks']]
        return False
    if not fetch_attestations(it):
        it['next'] = now + (HOT_POLL if hot else COLD_POLL)
        return False
    if it['ready_ts'] is None:
        it['ready_ts'] = round(time.time(), 3)
        log('ready', key=key, ready_ts=it['ready_ts'], seconds_after_source=round(it['ready_ts'] - it['src_ts'], 1))
    fee = it['p']['redeemFee']
    frm, to, ov = ctx
    data = run_calldata(it['cctp'], it['sigs'], it['vaa'], it['p'], fee)
    call = {'from': frm, 'to': to, 'data': data}
    try:
        gained = int(rpc(CHAIN, 'eth_call', [dict(call, gas=hex(SIM_GAS)), 'latest'] + ([ov] if ov else []))[2:66], 16)
    except ReadBudgetExceeded:
        raise
    except RuntimeError as e:
        msg = str(e)
        taken = 'Nonce already used' in msg or '4e6f6e636520616c72656164792075736564' in msg
        head = int(rpc(CHAIN, 'eth_blockNumber', []), 16)
        wn = None
        if taken:
            try:
                wn = winner(it, head - 8000)
            except ReadBudgetExceeded:
                raise
            except Exception:
                wn = None
            log('lost_before_send', key=key, reason='already_delivered', ready_ts=it['ready_ts'], winner_block=wn[0] if wn else None,
                winner_tx=wn[1] if wn else None, winner_relayer=wn[2] if wn else None, winner_ts=wn[3] if wn else None,
                seconds_winner_before_ready=(round(it['ready_ts'] - wn[3], 1) if wn else None), redeem_fee_usdc=fee)
            return True
        it['sim_fail'] += 1
        log('simulate_revert', key=key, error=msg[:300], n=it['sim_fail'])
        if it['sim_fail'] >= 5:
            return True
        it['next'] = now + 30
        return False
    if gained < fee:
        log('simulate_short', key=key, gained=gained, fee=fee)
        return True
    price = eth_usd()
    base_fee = int(rpc(CHAIN, 'eth_getBlockByNumber', ['latest', False])['baseFeePerGas'], 16)
    max_fee = base_fee + base_fee * BASE_FEE_HEADROOM_PCT // 100 + TIP_WEI
    est = int(rpc(CHAIN, 'eth_estimateGas', [call, 'latest'] + ([ov] if ov else [])), 16)
    gas_limit = est * GAS_MARGIN_NUM // GAS_MARGIN_DEN
    cap_wei = gas_limit * max_fee
    cap_usd = cap_wei / 1e18 * price
    row = dict(key=key, redeem_fee_usdc=fee, gross_usd=fee / 1e6, gas_estimate=est, gas_limit=gas_limit, max_fee=max_fee, base_fee=base_fee,
               gas_cap_wei=cap_wei, gas_cap_usd=round(cap_usd, 5), eth_usd=round(price, 2), ready_ts=it['ready_ts'],
               seconds_after_source=round(it['ready_ts'] - it['src_ts'], 1))
    if max_fee > MAX_FEE_WEI or gas_limit > MAX_GAS_LIMIT or cap_wei / 1e18 * ETH_REF_USD >= MAX_TX_USD:
        log('opportunity_skip', reason='fee_gas_or_usd_cap', **row)
        return True
    if fee / 1e6 <= cap_usd:
        log('opportunity_skip', reason='gross_not_above_gas_cap', **row)
        return True
    if MODE == 'live':
        bal = int(rpc(CHAIN, 'eth_getBalance', [frm, 'latest']), 16)
        if bal < cap_wei:
            log('opportunity_skip', reason='wallet_below_gas_cap', balance_wei=bal, **row)
            return True
        send_live(key, it, data, gas_limit, max_fee, fee, cap_wei, price)
        return True
    it['ready_block'] = int(rpc(CHAIN, 'eth_blockNumber', []), 16) - 40
    log('paper_sim', result='success', gained_usdc=gained, sim_block=it['ready_block'] + 40, **row)
    it['state'] = 'watch'
    it['checks'] = 0
    it['next'] = it['ready_ts'] + RESULT_CHECKS[0]
    return False


def load_state():
    try:
        s = json.loads(STATE.read_text())
    except Exception:
        s = {}
    s.setdefault('cursor', {})
    s.setdefault('pending', {})
    s.setdefault('done', {})
    s.setdefault('last_scan', 0)
    return s


def save_state(s):
    if len(s['done']) > 2000:
        for k in sorted(s['done'], key=lambda k: s['done'][k].get('t', 0))[:1000]:
            del s['done'][k]
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s))
    tmp.replace(STATE)


def main():
    if MODE == 'live' and not EXEC:
        sys.exit('EXECUTOR_ADDR_ARBITRUM / EXECUTOR_ADDR is not set: refusing to start without the gate-deployed executor')
    if not RELAY:
        sys.exit('RPC_RELAY_URL is not set')
    log('start', mode=MODE, executor=EXEC if MODE == 'live' else PAPER_EXEC, lane=LANE, sources=sorted(SOURCES))
    s = load_state()
    checked = False
    while True:
        try:
            now = time.time()
            if not checked:     # one reachability check of the two public attestation APIs (a known old message)
                a = http_json(IRIS.format(domain=6, tx='0xb2164e9248416066a834f44149748bb3e2059c1bc6947603775b3c348e152240'), 'iris')
                b = http_json(WHSCAN.format(wh=30, emitter=EMITTER, seq=85598), 'wormholescan')
                log('http_check', iris_ok=bool(a and a.get('messages')), wormholescan_ok=bool(b and (b.get('data') or {}).get('vaa')))
                checked = True
            if now - s['last_scan'] >= SCAN_INTERVAL:
                for name in SOURCES:
                    scan_source(s, name, now)
                s['last_scan'] = now
                log('scan', cursors=s['cursor'], pending=len(s['pending']))
                save_state(s)
            ctx = None
            for key in sorted(s['pending']):
                it = s['pending'][key]
                if time.time() < it['next']:
                    continue
                if ctx is None:
                    ctx = exec_ctx()
                if work_item(s, key, it, ctx, time.time()):
                    s['done'][key] = {'why': 'worked', 't': time.time()}
                    del s['pending'][key]
                save_state(s)
            now = time.time()
            nxt = min([s['last_scan'] + SCAN_INTERVAL] + [it['next'] for it in s['pending'].values()])
            time.sleep(max(1.0, min(60.0, nxt - now)))
        except ReadBudgetExceeded as e:
            utc = datetime.datetime.now(datetime.timezone.utc)
            midnight = (utc + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
            log('read_budget', error=str(e), sleep_s=int((midnight - utc).total_seconds()))
            time.sleep(max(60, (midnight - utc).total_seconds()))
        except Exception as e:
            log('loop_error', error=repr(e)[:400])
            time.sleep(30)


if __name__ == '__main__':
    main()
