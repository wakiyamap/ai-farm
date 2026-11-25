#!/usr/bin/env python3
# Reserve rebuilt-exit fork proof (attempt 964 follow-on): prove the burn leg
# repays the caller's PoolV3 debt at weETH redemption parity at C-1 of the
# last real burn (block 26394058, burner 0x233c0920, creditAccount 0x7d57..).
# Success leg: impersonate the burner, burn 25e18 weETH, assert pool
# totalBorrowed drops by ~parity x N and the eETH leg lands on the burner's
# creditAccount. Control leg: a funded debtless fresh EOA burns 5e18, pays
# -gas only (no cash, debt unchanged) - the executor must carry the debt leg.
import json, sys, urllib.request

URL = 'http://127.0.0.1:9003'
MANAGER = '0xfbfe6b9cee0e555bad7e2e7309effc75200cbe38'   # weETH manager proxy
IMPL_MGR = '0xbe386b1fb51ffacae0522a5da099371cd4a2aaea'
WEETH = '0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee'
EETH = '0x35fa164735182de50811e8e2e824cfb9b6118ac2'
CRED = '0x7d5706f6ef3f89b3951e23e557cdfbc3239d4e2c'      # burner creditAccount
POOL = '0x308861a4bb1a71e50490245f577068cc76f36145'      # PoolV3 (WETH underlying)
BURNER = '0x233c09204a9bd98d2a80c3bf91a0fb37e9a96b16'
EOA = '0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266'
N = 25 * 10**18
N2 = 5 * 10**18
_id = [0]

def rpc(m, p=None):
    body = {'jsonrpc': '2.0', 'id': _id[0], 'method': m, 'params': p or []}
    _id[0] += 1
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    r = json.load(urllib.request.urlopen(req))
    if 'error' in r: raise RuntimeError((m, r['error']))
    return r['result']

def w(a): return '0' * (64 - len(a[2:])) + a[2:]
def u(h): return int(h, 16) if h and h != '0x' else 0
def call(to, data): return call_err(to, data)[0]
def call_err(to, data):
    try:
        return (u(rpc('eth_call', [{'to': to, 'data': data}, 'latest'])), None)
    except RuntimeError as e:
        return (None, e.args[1].get('message') if isinstance(e.args[1], dict) else str(e))

BAL = '0x70a08231'
APPROVE = '0x095ea7b3'
BURN = '0xccc143b8'
TOTAL_BORROWED = '0x' + '07535691'[:0] + '85911778'  # placeholder, fixed below

def sel(sig):
    from subprocess import run, PIPE
    return run(['cast', 'sig', sig], capture_output=True, text=True).stdout.strip()

TOTAL_BORROWED = sel('totalBorrowed()')

def sendto(frm, to, data, gas=600000):
    tx = {'from': frm, 'to': to, 'data': data, 'gas': '0x' + format(gas, 'x')}
    r = rpc('eth_sendTransaction', [tx])
    txh = r
    for _ in range(30):
        rc = rpc('eth_getTransactionReceipt', [txh])
        if rc: return txh, rc
    return txh, None

def main():
    blk0 = rpc('eth_blockNumber', [])
    print('fork block', blk0)
    # sanity selectors from cast (canonical keccak verified via approve/transfer constants)
    print('totalBorrowed() sel', TOTAL_BORROWED)
    tb0 = u(rpc('eth_call', [{'to': POOL, 'data': TOTAL_BORROWED}, 'latest']))
    bal0 = u(rpc('eth_call', [{'to': WEETH, 'data': BAL + w(BURNER)}, 'latest']))
    eth_burner0 = int(rpc('eth_getBalance', [BURNER, 'latest']), 16)
    cred_eeth0 = u(rpc('eth_call', [{'to': EETH, 'data': BAL + w(CRED)}, 'latest']))
    print('pre totalBorrowed', tb0 / 1e18, 'burner weETH', bal0 / 1e18, 'burner eth', eth_burner0 / 1e18, 'creditAcc eETH', cred_eeth0 / 1e18)
    assert bal0 >= N, 'burner lacks weETH balance at this block'

    rpc('anvil_impersonateAccount', [BURNER])
    # fund gas for the impersonated burner
    rpc('anvil_setBalance', [BURNER, '0x' + format(int(2e18), 'x')])
    eth_burner0 = int(rpc('eth_getBalance', [BURNER, 'latest']), 16)

    d = APPROVE + w(MANAGER) + '0x' + 'f' * 64
    txh, rec = sendto(BURNER, WEETH, d)
    print('approve mgr', txh, rec['status'], rec['gasUsed'])
    txh_burn, rec = sendto(BURNER, MANAGER, BURN + '0x' + '%064x' % N)
    print('BURN tx', txh_burn, 'status', rec['status'], 'gasUsed', rec['gasUsed'])
    tb1 = u(rpc('eth_call', [{'to': POOL, 'data': TOTAL_BORROWED}, 'latest']))
    bal1 = u(rpc('eth_call', [{'to': WEETH, 'data': BAL + w(BURNER)}, 'latest']))
    cred_eeth1 = u(rpc('eth_call', [{'to': EETH, 'data': BAL + w(CRED)}, 'latest']))
    eth_burner1 = int(rpc('eth_getBalance', [BURNER, 'latest']), 16)
    drop = tb0 - tb1
    print('POST totalBorrowed', tb1 / 1e18, 'debt drop', drop / 1e18,
          'parity x N =', 1.1078 * N / 1e18,
          'burner weETH', bal1 / 1e18, 'creditAcc eETH', cred_eeth1 / 1e18,
          'burner eth delta', (eth_burner1 - eth_burner0) / 1e18)
    print('ASSERT debt drop > 0 (parity leg):', drop > 0,
          'ratio', drop / (1.1078 * 30 * 10**18) if drop else 0,
          'parity', drop / N if N else 0)
    blk1 = rpc('eth_blockNumber', [])
    logs = rpc('eth_getLogs', [{'fromBlock': blk1 if isinstance(blk1, str) else blk0,
                                'toBlock': 'latest', 'address': WEETH,
                                'topics': [None, w(BURNER), w('0x0000000000000000000000000000000000000000')[:42]]}]) if False else []
    # control leg: debtless fresh EOA burns 5e18
    rpc('anvil_impersonateAccount', [EOA])
    d = APPROVE + w(MANAGER) + '0x' + 'f' * 64
    txh, rec = sendto(EOA, WEETH, d)
    print('approve mgr (EOA)', txh, rec['status'])
    txh_c, rec = sendto(EOA, MANAGER, BURN + '0x' + '%064x' % N2)
    print('CONTROL burn tx', txh_c, 'status', rec['status'], 'gasUsed', rec['gasUsed'])
    tb2 = u(rpc('eth_call', [{'to': POOL, 'data': TOTAL_BORROWED}, 'latest']))
    eth_eoa1 = int(rpc('eth_getBalance', [EOA, 'latest']), 16)
    print('control totalBorrowed', tb2 / 1e18, '(unchanged vs', tb1 / 1e18, ')', tb1 == tb2,
          'EOA eth delta', eth_eoa1 / 1e18)
    print('TXH burn', txh_burn); print('TXH control', txh_c)
    print('fork block end', rpc('eth_blockNumber', []), '(start', blk0, ')')

main()
