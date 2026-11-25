# lead 157 / morpho-farmband2-base fix round 2 (run 9ca761d0): per-occurrence C-1
# detection + measured gas for the three counted captures (review 1095 blockers 2/4).
# Reads: market/position getters at the capture's PARENT block tag, the pinned feed
# answer before C, the capture receipt gasUsed + block baseFee + tx priority fee.
import json, urllib.request, sys

RELAY = 'http://127.0.0.1:8545/base?lane=research'
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'

def rpc(m, p):
    d = json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode()
    j = json.load(urllib.request.urlopen(urllib.request.Request(RELAY, d, {'content-type': 'application/json'})))
    if 'error' in j: raise Exception(m + ' ' + json.dumps(j['error'])[:200])
    return j['result']

def w(h, i): return int(h[2 + i * 64: 2 + i * 64 + 64], 16)

def addr(a): return a[2:].lower().rjust(64, '0')

SEL_MARKET = '0x5c60e39a'
SEL_POS = '0x93c52062'
TOPIC_ANSWER_UPDATED = '0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'

# capture: (name, market id, borrower, C block, capture tx, feeds[(addr,decimals)],
#           collateral token, collDec, lltv, usd answer decimals)
CAPS = [
 dict(name='cbBTC-53486211', id='0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836',
      borrower='0x63a905f49590b5428e66845b4fb240031a09bbad', C=53486211,
      tx='0xc25f5f060e4fba181c77612b484a53ee0d1ac46e3d63523be1c94ff1878a4181',
      feeds=[('0xeb3ad4395924b76eb64b3d6ababa0b62875b1a1f', 18), ('0x137233996b6586a110bb7a753248e26cc0307b1b', 18)],
      collDec=8, lltv=860000000000000000, repaid=495547172, seized=683970),
 dict(name='cbETH-54926448', id='0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d',
      borrower='0xd1a9a065a5edc85a73e7ea81b5032133548235a3', C=54926448,
      tx='0xfcc10c946122eca99a58115a7d6fe9400f826b0b35c370d2e216374127569d5d',
      feeds=[('0x71e021bc2e8a709b72ac7b6036e5b2bf30f263d0', 8)],
      collDec=18, lltv=770000000000000000, repaid=211674847, seized=94132158690255955),
 dict(name='cbBTC-56677288', id='0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836',
      borrower='0x85049883759d4f2e3e9d23364129ddf5bb99dcb1', C=56677288,
      tx='0x4812fa9f9bce933fb5e38edd8667e629b3e7df0aea8563436dcb65a65c1f8b46',
      feeds=[('0xeb3ad4395924b76eb64b3d6ababa0b62875b1a1f', 18), ('0x137233996b6586a110bb7a753248e26cc0307b1b', 18)],
      collDec=8, lltv=860000000000000000, repaid=102088874, seized=149884),
]

out = {}
for c in CAPS:
    C = c['C']; P = hex(C - 1)
    r = rpc('eth_call', [{'to': MORPHO, 'data': SEL_MARKET + addr(c['id'])}, P])
    ta, ts = w(r, 2), w(r, 3)
    pr = rpc('eth_call', [{'to': MORPHO, 'data': SEL_POS + addr(c['id']) + addr(c['borrower'])}, P])
    shares, collat = w(pr, 1) & ((1 << 128) - 1), w(pr, 2)
    # last pinned feed answer strictly before C (the price the bot would have held at C-1)
    usd6 = None
    for (f, dec) in c['feeds']:
        logs = rpc('eth_getLogs', [{'address': [f], 'topics': [TOPIC_ANSWER_UPDATED],
                                    'fromBlock': hex(max(1, C - 30000)), 'toBlock': hex(C - 1)}])
        if not logs: continue
        ans = int(logs[-1]['topics'][1], 16)
        if ans >= 1 << 255: ans -= 1 << 256  # int256 topics are two's complement
        if ans <= 0: continue
        u6 = ans // 10**(dec - 6) if dec >= 6 else ans * 10**(6 - dec)  # -> 1e6 USD units
        if usd6 is None or u6 > usd6: usd6 = u6
        out.setdefault(c['name'] + '_feedlog', []).append((f, logs[-1]['blockNumber']))
    debt = shares * ta // ts if ts else 0
    # FIXED maxDebt (USDC 1e6 assets): collat x usd6 x lltv / 10**(collDec+18)
    maxDebt = collat * usd6 * c['lltv'] // 10**(c['collDec'] + 18) if usd6 else None
    # seized quote (collateral units): debt x 1e18 x 10**collDec / (lltv x usd6)
    seizedEst = debt * 10**18 * 10**c['collDec'] // (c['lltv'] * usd6) if usd6 else None
    rec = dict(ta=ta, ts=ts, borrowShares=shares, collateral=collat, usd6=usd6,
               debt=debt, maxDebt_fixed=maxDebt, liquidatable_C1=(debt > maxDebt) if maxDebt is not None else None,
               debt_over_maxdebt=round(debt / maxDebt, 4) if maxDebt else None,
               seizedEst_units=seizedEst, seized_units_C= c['seized'],
               repaid_C=c['repaid'])
    # measured gas of the incumbent capture tx
    rc = rpc('eth_getTransactionReceipt', [c['tx']])
    blk = rpc('eth_getBlockByNumber', [hex(C), False])
    tx = rpc('eth_getTransactionByHash', [c['tx']])
    gasUsed = int(rc.get('gasUsed', '0x0'), 16)
    baseFee = int(blk.get('baseFeePerGas') or '0', 16)
    pri = int(tx.get('maxPriorityFeePerGas') or tx.get('gasTipCap') or '0', 16)
    rec['gasUsed_incumbent'] = gasUsed
    rec['gas_fee_wei'] = baseFee + pri
    rec['gas_usd_at_1900'] = round(gasUsed * (baseFee + pri) / 1e18 * 1900, 3)
    rec['gas_incumbent_status'] = rc.get('status')
    out[c['name']] = rec
print(json.dumps(out, indent=1, default=str))
json.dump(out, open('scratch/mb157b-measure.json', 'w'), indent=1, default=str)
print('MEASURE-OK')
