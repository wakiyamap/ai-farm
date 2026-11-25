# Fork proof 4 for morpho-farmband2-base (lead 157, run 9ca761d0, review 1095 blockers 1/2/4):
# the two captures proven liquidatable at their C-1 state (cbBTC 53486211 borrower
# 0x63a905f4..., debt 495.547 USD vs maxDebt 495.117; cbBTC 56677288 borrower
# 0x85049883..., debt 102.089 vs maxDebt 101.981 - scratch/mb157b-measure.json),
# with the FINAL bot calldata shape (the same seizure quote + full-seizure swap amount
# the fixed bot.js builds: amt1 = min(debt x 1e18 x 10^collDec / (lltv x usd6), collateral)
# x 999/1000, flash = debt + 0.1 USDC margin, minProfit 1.00 USDC) on the manifest artifact.
# Per capture: reset C-1 -> fund owner -> deploy -> owner whitelist setup -> guard tx
# (minProfit = flash x 100, expect NO_PROFIT revert, state unchanged) -> success tx ->
# owner-wallet USDC delta. Lease base for the run, release on exit.
import json, subprocess, sys, urllib.request
from Cryptodome.Hash import keccak

F = 'http://127.0.0.1:9001'
RELAY = 'http://127.0.0.1:8545/base?lane=research'
MORPHO = '0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
USDC = '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
POOL_CB = '0xfbb6eed8e7aa03b138556eedaf5d271a5e1e43ef'   # cbBTC/USDC UniV3 (runtime-whitelisted)
ORACLE_CB = '0x663becd10dae6c4a3dcd89f1d76c1174199639b9'
IRM = '0x46415998764c29ab2a25cbea6254146d50d22687'
LLTV = 860000000000000000
OWNER = '0x1111111111111111111111111111111111111111'
POOLF = '0xfdebedc97d56edd31abdcb887570546b257964f2'
CBBTC = None  # derived from ctor word 2 below

def addr(a): return a[2:].lower().rjust(64, '0')
def w(n): return format(n, '064x')
def k256(b):
    if isinstance(b, str): b = b.encode()
    h = keccak.new(digest_bits=256); h.update(b); return h.digest().hex()
def rpc_fork(m, p):
    d = json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode()
    j = json.load(urllib.request.urlopen(urllib.request.Request(F, d, {'content-type': 'application/json'})))
    if 'error' in j: raise Exception(str(j.get('error'))[:200])
    return j['result']
def rpc_relay(m, p):
    d = json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode()
    j = json.load(urllib.request.urlopen(urllib.request.Request(RELAY, d, {'content-type': 'application/json'})))
    if 'error' in j: raise Exception(str(j.get('error'))[:200])
    return j['result']
def sh(*cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit('FAILED: %s\n%s\n%s' % (' '.join(cmd), p.stdout[-500:], p.stderr[-500:]))
    return p.stdout

sh('fork', 'lease', 'base', '25', 'lead157-proof4')
try:
    args = json.load(open('scratch/mb157-proof.json'))['ctor_args']  # verified byte-equal to the manifest
    CBBTC = '0x' + args[2:][128:192][24:64]; assert len(CBBTC) == 42, CBBTC

    SEL_EXEC_LIQUIDATE = '0x' + k256('liquidate((address,address,address,address,uint256),address,uint256,uint256,uint256,address,bytes,address,address,bytes)')[:8]
    SEL_POOL_SWAP = '0x128acb08'
    SEL_SETPOOL = '0x' + k256('setPoolAllowed(address,bool)')[:8]
    SEL_SETCOLL = '0x' + k256('setCollateralAllowed(address,bool)')[:8]
    MAX_SQRT_RATIO_M1 = 'fffd8963efd1fc6a506488495d951d5263988d25'

    def encPoolSwap(recipient, amount):
        t0, t1 = sorted([USDC.lower(), CBBTC.lower()])
        return SEL_POOL_SWAP + addr(recipient) + w(0) + w(amount) + MAX_SQRT_RATIO_M1.rjust(64, '0') + \
            w(0xa0) + w(0x40) + addr(t0) + addr(t1)
    def encExecutorCall(borrower, repaidShares, flashAmount, minProfit, swapData1):
        d1len = (len(swapData1) - 2) // 2
        data1_off = 14 * 32
        data2_off = data1_off + 32 + 32 * ((d1len + 31) // 32)
        return SEL_EXEC_LIQUIDATE + addr(USDC) + addr(CBBTC) + addr(ORACLE_CB) + addr(IRM) + w(LLTV) + \
            addr(borrower) + w(repaidShares) + w(flashAmount) + w(minProfit) + addr(POOL_CB) + \
            w(data1_off) + w(0) + w(0) + w(data2_off) + \
            w(d1len) + swapData1[2:] + '0' * ((32 * ((d1len + 31) // 32) - d1len) * 2) + \
            w(1) + '00' + '0' * 62
    def bal_of(who):
        return int(rpc_fork('eth_call', [{'to': USDC, 'data': '0x70a08231' + addr(who)}, 'latest']), 16)
    import time as _t
    def send(txj):
        h = rpc_fork('eth_sendTransaction', [txj])
        for _ in range(40):
            rc = rpc_fork('eth_getTransactionReceipt', [h])
            if rc: return h, rc
            _t.sleep(0.3)
        raise Exception('no receipt ' + h)
    def trace(h):
        t = sh('fork', 'trace', 'base', h)
        return json.loads(t[t.index('{'):]) if '{' in t else {}

    MEAS = json.load(open('scratch/mb157b-measure.json'))
    RES = {}
    for name, C, borrower, RS in [
        ('cbBTC-53486211', 53486211, '0x63a905f49590b5428e66845b4fb240031a09bbad', 439547372492091),
        ('cbBTC-56677288', 56677288, '0x85049883759d4f2e3e9d23364129ddf5bb99dcb1', 90424969508907)]:
        m = MEAS[name]
        usd6 = int(m['usd6']); debt = int(m['debt']); collat = int(m['collateral'])
        BONUS_BPS = 10430  # the pinned seizure bonus (measured seized/repaid = 1.0436 at C-1 prices, review 1095: the swap amount must not exceed the actual seizure - the executor caps the pool payment at the seized balance)
        seizedEst = debt * BONUS_BPS * 10**8 // (usd6 * 10000)
        amt1 = (min(seizedEst, collat) * 999) // 1000
        flash = debt + 100000
        sh('fork', 'reset', 'base', str(C - 1))
        sh('fork', 'fund', 'base', OWNER, '1')
        out = sh('fork', 'deploy', 'base', 'scratch/morpho-farmband-base/contracts/out/MorphoFarmLiquidator.sol/MorphoFarmLiquidator.json', OWNER, '--args', args)
        EXEC = [l for l in out.split('\n') if l.strip().startswith('0x') and len(l.strip()) == 42][-1].strip()
        for sel, a in [(SEL_SETPOOL, POOL_CB), (SEL_SETPOOL, POOLF), (SEL_SETCOLL, '0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22')]:
            send({'from': OWNER, 'to': EXEC, 'data': sel + addr(a) + w(1), 'gas': '0x61a80'})
        swapData1 = encPoolSwap(EXEC, amt1)
        cd = encExecutorCall(borrower, RS, flash, 1000000, swapData1)
        cd_guard = cd[:8 + 8 * 64] + w(flash * 100) + cd[8 + 8 * 64 + 64:]  # bot.js minProfit -> flash x 100
        txg = {'from': OWNER, 'to': EXEC, 'data': cd_guard, 'gas': '0x13d620', 'gasPrice': '0xb2d05e00', 'value': '0x0'}
        hg, rcg = send(txg)
        tg = trace(hg) if rcg.get('status') != '0x1' else {'status': rcg.get('status')}
        tg = {k: v for k, v in tg.items()}
        o0 = bal_of(OWNER); b0 = bal_of(EXEC)
        h1, rc1 = send(dict(txg, data=cd))
        t1 = trace(h1)
        o1 = bal_of(OWNER); b1 = bal_of(EXEC)
        delta = o1 - o0
        blk = rpc_relay('eth_getBlockByNumber', [hex(C), False])
        baseFee = int(blk.get('baseFeePerGas') or '0', 16)
        gu = t1.get('gasUsed', 0)
        gu = int(gu, 16) if isinstance(gu, str) else int(gu)
        gas_usd = round(gu * (baseFee + 10**8) / 1e18 * 1934, 3)
        RES[name] = dict(executor=EXEC, reset_block=C - 1, borrower=borrower,
                         debt_C1=debt, usd6=usd6, seizedEst_units=seizedEst, collateral=collat, amt1=amt1,
                         guard_tx=hg, guard_revert=tg.get('revertReason') or tg.get('error') or tg.get('execReason') or tg.get('status'),
                         success_tx=h1, success_status=t1.get('status'), success_gasUsed=gu,
                         wallet_delta_units=delta, executor_leftover_units=b1 - b0,
                         block_baseFee_wei=baseFee, gas_usd_at_block=gas_usd)
        print(name, json.dumps(RES[name], indent=1)[:600])
        assert delta > 0 and (tg.get('revertReason') or '').upper().find('PROFIT') >= 0, (delta, tg.get('revertReason'))
    json.dump(RES, open('scratch/mb157b-proof4.json', 'w'), indent=1)
    print('PROOF4-OK' if all(v['wallet_delta_units'] > 0 for v in RES.values()) else 'PROOF4-FAILED')
finally:
    sh('fork', 'release', 'base')
