#!/usr/bin/env python3
"""Count WBETH wrap/unwrap events over the 7-day window and inspect topic0 set."""
import json, subprocess, collections, sys

def raw(method, params):
    out = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', 'ethereum', method, json.dumps(params)],
                         capture_output=True, text=True).stdout
    d = json.loads(out)
    if 'error' in d:
        raise SystemExit('RPC error: ' + json.dumps(d['error'])[:200])
    return d['result']

FR, TO = 0x1938F58, 0x193CF44   # placeholders, replaced below
FR, TO = 26413784, 26464036
WRAP = '0xa2E3356610840701BDf561a53974510Ae27E2e1'.lower()
WRAP = '0xa2E3356610840701BDf5611a53974510Ae27E2e1'
UNWRAP = '0x79973d557CD9dd87eb61E250cc2572c990e20196'

T = {
 '0x0b4e9390054347e2a16d95fd8376311b0d2deedecba526e9742bcaa40b059f0b': 'ExchangeRateUpdated(address,uint256)',
 '0x3df77beb5db05fcdd70a30fc8adf3f83f9501b68579455adbd100b8180940394': 'OracleUpdated(address)',
 '0xfbe5b6cbafb274f445d7fed869dc77a838d8243a22c460de156560e8857cad03': 'OperatorUpdated(address,address)',
 '0xc6826629852f9e6617c80ac221f1ea00b4fb5c6ee3d58982080816550c01e599': 'EthReceiverUpdated(address,address)',
 '0xe32c4b34261b430739ef30d727d062f9fdd6410be2080e6fd875a6015f40de83': 'DepositEth(address,uint256,uint256,address)',
 '0x6f159dc1a889982fdc908cb2b9a48d36d718ed0c0c8c9ef565c4857e0f00a462': 'SuppliedEth(address,uint256)',
 '0x721a8f86a9fdbdbdd40ad38486cae32f7ee0a9f16c9df4596ea18bb01853efdf': 'MovedToStakingAddress(address,uint256)',
 '0xe1ea856a2dd2650e9ab8bb416f893add49ac95f8364e47b4395a3ada9b0ccc2c': 'RequestWithdrawEth(address,uint256,uint256)',
 '0x56d2bc55f552daa5d7bf4883dc0f73fb82309ff0beee747fca1dcfbd501226e0': 'MovedToUnwrapAddress(address,uint256)',
 '0x1e57e3bb474320be3d2c77138f75b7c3941292d647f5f9634e33a8e94e0e069b': 'EtherReceived(address,uint256)',
 '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef': 'Transfer(address,address,uint256)',
 '0xab8530f87dc9b59234c4623bf917212bb2536d647574c8e7e5da92c2ede0c9f8': 'Mint(address,address,uint256)',
 '0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5': 'Burn(address,uint256)',
 '0x96d07fd2bc9180dce2d22cb77edc26050eeb85876cff9714d58346b2974a8665': 'RequestWithdraw(address,uint256,uint256,uint256)',
 '0x11636acb273b17b8e23cc6bcaf0758c5159a25ff5df82ca4134eb012ab949e46': 'ClaimWithdraw(address,uint256,uint256)',
 '0x249d8eb76d5a22983620d741de2470148d1a9a26ab923aec4262770690d11ebc': 'Allocate(address,uint256)',
 '0x4f9c5ea9e96203f2ca18a6ed770609b95cde3cc4ad2fb31b0ae5ee62f8753bd0': 'RechargeFromRechargeAddress(address,uint256)',
 '0xb373deb6f9dcc6743e3c80f52fd8a676da3a5e0d3aae33c48f1c561c94d2369f': 'MoveFromWrapContract(address,uint256)',
 '0x4c1180bdd12ad3ee9fd704c1be48d07859d001312135d5197b16382a409925df': 'MoveToEthBackAddress(address,uint256)',
 '0x03e62bb5e26d7662cb296d342ec4b27d5e8f2b40179677602eeb547714723daf': 'EthStakedUpdated(address,uint256)',
 '0x2c21a6c9b9bdee92536b9e6b99cbbabcc692423f4c08b6285788f854f1d8c3ea': 'LockTimeUpdated(address,uint256)',
}

def counts(addr, topic_list, fr=FR, to=TO):
    logs = raw('eth_getLogs', [{'fromBlock': hex(fr), 'toBlock': hex(to), 'address': addr,
                                'topics': [list(topic_list)]}])
    c = collections.Counter(l['topics'][0].lower() for l in logs)
    return c, logs

# 1) wrap token: all protocol events except Transfer
wrap_topics = [t for t in T if T[t] != 'Transfer(address,address,uint256)']
c, logs = counts(WRAP, wrap_topics)
print(f'WRAP {FR}..{TO} (protocol events, Transfer excluded): {len(logs)} logs')
for t, n in c.most_common():
    print(f'  {n:6d}  {T.get(t, "UNKNOWN " + t)}')
print('  unseen topic0:', {T.get(t, t) for t in {l["topics"][0].lower() for l in logs}} - set(c))

# 2) unwrap token: all its events
unwrap_topics = [t for t in T if t not in ('0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',)]
cu, logsu = counts(UNWRAP, unwrap_topics)
print(f'UNWRAP {FR}..{TO}: {len(logsu)} logs')
for t, n in cu.most_common():
    print(f'  {n:6d}  {T.get(t, "UNKNOWN " + t)}')

# 3) control: Transfer on wrap over the same window
ct, _ = counts(WRAP, ['0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'])
print('CONTROL Transfer on WRAP same window:', dict(ct))

# 4) who emits ExchangeRateUpdated (topic1 = oracle) and DepositEth / Allocate details
ex = raw('eth_getLogs', [{'fromBlock': hex(FR), 'toBlock': hex(TO), 'address': WRAP,
        'topics': ['0x0b4e9390054347e2a16d95fd8376311b0d2deedecba526e9742bcaa40b059f0b']}])
print('ExchangeRateUpdated oracle topic1s:', collections.Counter(l['topics'][1] for l in ex))
