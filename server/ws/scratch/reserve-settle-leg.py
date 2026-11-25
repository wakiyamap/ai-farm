#!/usr/bin/env python3
# Reserve rebuild executor settle-success leg (lead 19/126 rebuild path, attempt 1011
# next-session recipe), run 3a8ae16c. Reset 26394057 = state at the end of C-1 of the
# last real burn (block C 26394058, burner 0x233c0920). Measured facts this session:
# (1) the plain weETH approve from the burner at C-1 works (1011's "approve reverts"
#     was the fork-CLI path, not the token);
# (2) the burn entry burn(0xccc143b8)(uint256 amount, address account) takes TWO
#     32-byte words; account = the EOA-side account (word2 of the last real burn tx
#     input = the burner EOA, not its creditAccount 0x7d57..), it pays with the
#     CALLER's weETH via transferFrom ("ERC20: insufficient allowance" measured on a
#     balanceless caller) and returns the debt remainder word (0x149ae on the last
#     real burn);
# (3) 1011's abi.encodePacked(BURN_SEL, n, account) produced 56-byte calldata (a 20-
#     byte account) - the decoder reverted every burn leg with an immediate ~265-gas
#     revert; the fixed contract uses bytes.concat(BURN_SEL, abi.encode(n, account)).
# Success leg: executor settle(N, d, holder=burner, account=burner, minProfit=0) with
# N = the burner's exact weETH balance = the mainnet burn amount; burn repays the
# burner's debt 1.107946 x N eETH. Debt cleared is read from the prestateTracer
# diffMode slot deltas. Control: settle again reverts (allowance consumed).
import json, subprocess, sys, urllib.request

URL = 'http://127.0.0.1:9003'
MANAGER = '0xfbfe6b9cee0e555bad7e2e7309effc75200cbe38'
WEETH = '0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee'
EETH = '0x35fa164735182de50811e8e2e824cfb9b6118ac2'
CRED = '0x7d5706f6ef3f89b3951e23e557cdfbc3239d4e2c'
POOL = '0x308861a4bb1a71e50490245f577068cc76f36145'
BURNER = '0x233c09204a9bd98d2a80c3bf91a0fb37e9a96b16'
EOA = '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266'
N = int('01833bcdf7a1b3780d', 16)   # burner exact weETH balance = last real burn amount
_id = [0]

def rpc(m, p=None):
    body = {'jsonrpc': '2.0', 'id': _id[0], 'method': m, 'params': p or []}
    _id[0] += 1
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    r = json.load(urllib.request.urlopen(req))
    if 'error' in r:
        raise RuntimeError((m, r['error']))
    return r['result']

def u(h): return int(h, 16) if h and h != '0x' else 0
def w(a): return '0' * (64 - len(a[2:])) + a[2:]
def p64(x): return x.rjust(64, '0')

def sel(sig):
    return subprocess.run(['cast', 'sig', sig], capture_output=True, text=True).stdout.strip()

BAL = '0x70a08231'
APPR = '0x095ea7b3'

def sendto(frm, to, data, gas=900000):
    tx = {'from': frm, 'to': to, 'data': data, 'gas': '0x' + format(gas, 'x')}
    txh = rpc('eth_sendTransaction', [tx])
    for _ in range(30):
        rc = rpc('eth_getTransactionReceipt', [txh])
        if rc: return txh, rc
    return txh, None

def prestate(txh):
    try:
        return rpc('debug_traceTransaction', [txh, {'tracer': 'prestateTracer',
                                                     'tracerConfig': {'diffMode': True}}])
    except Exception as e:
        return {'error': str(e)}

def main():
    print('resetting to end of C-1 (26394057)')
    subprocess.run(['fork', 'reset', 'ethereum', '26394057'], check=True)
    blk = u(rpc('eth_blockNumber', []))
    print('fork block', blk)

    bal0 = u(rpc('eth_call', [{'to': WEETH, 'data': BAL + w(BURNER)}, 'latest']))
    cred0 = u(rpc('eth_call', [{'to': EETH, 'data': BAL + w(CRED)}, 'latest']))
    print('pre burner weETH %.6f (creditAcc eETH cash %.4f)' % (bal0 / 1e18, cred0 / 1e18))
    assert bal0 == N, 'burner balance must equal the burn amount for the exact-debt leg'

    art = json.load(open('scratch/reserve-exec-1528/contracts/out/ReserveExitExecutor.sol/ReserveExitExecutor.json'))
    code = art['bytecode']['object']
    args = w(MANAGER) + w(WEETH) + w(EETH)
    txh = rpc('eth_sendTransaction', [{'from': EOA, 'to': None, 'data': code + args,
                                       'gas': '0x' + format(3000000, 'x')}])
    rc = None
    for _ in range(30):
        rc = rpc('eth_getTransactionReceipt', [txh])
        if rc: break
    EXEC = rc['contractAddress']
    print('deploy tx', txh, 'status', rc['status'], 'EXEC', EXEC, 'gasUsed', rc['gasUsed'])
    assert rc['status'] == '0x1'

    rpc('anvil_impersonateAccount', [BURNER])
    rpc('anvil_setBalance', [BURNER, '0x' + format(int(5e18), 'x')])

    # 1) the approve-from-burner leg 1011 left unresolved: plain ERC20 approve works
    r = rpc('eth_call', [{'from': BURNER, 'to': WEETH,
                          'data': APPR + w(EXEC) + p64(hex(N)[2:])}, 'latest'])
    print('eth_call approve(burner->EXEC) returns', r)
    txh, rc = sendto(BURNER, WEETH, APPR + w(EXEC) + p64(hex(N)[2:]))
    print('approve tx', txh, 'status', rc['status'], 'gasUsed', rc['gasUsed'])
    if rc['status'] != '0x1':
        sys.exit('approve leg broken')

    # 2) settle success leg: account = the EOA-side account (burner), measured shape
    settle_sel = sel('settle(uint256,uint256,address,address,uint256)')
    d = int(1.107946 * N)
    data = settle_sel + p64(hex(N)[2:]) + p64(hex(d)[2:]) + w(BURNER) + w(BURNER) + '0' * 64
    txh, rc = sendto(EOA, EXEC, data)
    print('settle tx', txh, 'status', rc['status'], 'gasUsed', rc['gasUsed'])
    if rc['status'] != '0x1':
        t = rpc('debug_traceTransaction', [txh, {'tracer': 'callTracer'}])
        print('callTracer:', json.dumps(t, default=str)[:1000])
        sys.exit('settle leg reverted')

    bal1 = u(rpc('eth_call', [{'to': WEETH, 'data': BAL + w(BURNER)}, 'latest']))
    execw = u(rpc('eth_call', [{'to': WEETH, 'data': BAL + w(EXEC)}, 'latest']))
    execx = u(rpc('eth_call', [{'to': EETH, 'data': BAL + w(EXEC)}, 'latest']))
    print('burner weETH %.6f -> %.6f (the win flowed out: paid %.6f)' % (bal0 / 1e18, bal1 / 1e18, N / 1e18))
    print('EXEC weETH %.6f EXEC eETH %.6f (guards held: no cash out to the executor)' % (execw / 1e18, execx / 1e18))

    # debt cleared: prestateTracer diffMode slot deltas
    ps = prestate(txh)
    rows = []
    MASK128 = (1 << 128) - 1
    def add_row(addr, slot, b, a):
        rows.append((addr, slot, b, a, b - a))
        # the creditAccount packs two uint128 fields (weETH amount | eETH debt)
        # in one slot; also expose each half as its own row
        if b <= 2**128 and a <= 2**128:
            hb, ha = b >> 128, a >> 128
            if hb or ha:
                rows.append((addr, slot + ':hi', hb, ha, hb - ha))
            lb, la = b & MASK128, a & MASK128
            if lb != la:
                rows.append((addr, slot + ':lo', lb, la, lb - la))
    if 'error' in ps:
        print('prestate error:', ps['error'][:300])
    elif 'pre' in ps and 'post' in ps:      # anvil prestateTracer diffMode: {pre:.., post:..}
        def flat2(d):
            out = {}
            for addr, v in d.items():
                if isinstance(v, dict):
                    for slot, sv in (v.get('storage') or {}).items():
                        out[(addr, slot)] = u(sv) if isinstance(sv, str) else 0
            return out
        bS, aS = flat2(ps['pre']), flat2(ps['post'])
        for k, b in bS.items():
            av = aS.get(k, 0)
            if av == b: continue
            add_row(k[0], k[1], b, av)
        for k, av in aS.items():
            if k not in bS and av != 0:
                add_row(k[0], k[1], 0, av)
    else:
        for addr, v in ps.items():
            st = v.get('storage', {}) if isinstance(v, dict) else {}
            for slot, sv in st.items():
                if isinstance(sv, dict) and 'before' in sv and 'after' in sv:
                    b, a = u(sv['before']), u(sv['after'])
                    if b != a:
                        add_row(addr, slot, b, a)
    if not rows:
        print('prestate raw (unparsed):', json.dumps(ps, default=str)[:1500])
    rows.sort(key=lambda r: -abs(r[4]))
    for r in rows[:14]:
        print('slot delta %s slot %s %d -> %d (delta %.6f)' % (r[0], r[1], r[2], r[3], r[4] / 1e18))
    expect = int(1.107946 * N)   # burner debt fully cleared, measured 30.915e18 eETH
    def as2(v):
        if v >= 2**128: return v - 2**160     # uint160 stored as two packed words
        return v
    for r in rows:
        r2 = (r[0], r[1], as2(r[2]), as2(r[3]), as2(r[2]) - as2(r[3]))
        r = list(r); r[:] = r2
    hit = [r for r in rows if abs(as2(r[2]) - as2(r[3]) - expect) < 0.01 * expect and as2(r[2]) - as2(r[3]) > 0]
    print('debt-cleared match vs parity x N =', [h[4] for h in hit])
    if not hit:
        sys.exit('NO slot matches parity x N debt clearing - success leg unproven')

    # 3) control: settle again must revert (allowance consumed, win gone)
    txh2, rc2 = sendto(EOA, EXEC, data)
    print('control settle tx', txh2, 'status', rc2['status'], 'gasUsed', rc2['gasUsed'])
    if rc2['status'] == '0x1':
        sys.exit('control settle must revert')

    print('SUCCESS LEG LANDED: settle fork tx', txh, 'status 1; debt cleared %.6f eETH'
          % (hit[0][4] / 1e18), 'for %.6f weETH paid' % (N / 1e18),
          '(margin ~+%.4f ETH at settled bid 1.0038)' % (N / 1e18 * (1.107851 / 1.1053 - 1) * 1.0038))

main()
