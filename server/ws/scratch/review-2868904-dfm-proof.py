"""trial-dfm-pegkeeper-arbitrum fork proof: lease, reset, deploy, fund, probe, non-owner, guard (NoProfit), success,
repeat (action delay: nothing to take), leftovers, allowances, runtime code, release. One script, one Arbitrum lease.

defi.money PegKeeperRegulator 0xf2b12abe...: update(pk, beneficiary) pays the beneficiary 20 pct of the keeper's new
profit as Curve pool LP. The script resets to the parent block of an incumbent update and takes the same update
through the farm executor (StepArb) with the calldata the bot itself builds (bot.py).
usage: proof.py [parent block] [result file]   default 526250482 = parent of the incumbent's 0x20b5ad22... (block
       526,250,483, 13:36:38Z: USDT keeper provided 26.69 MONEY, caller share 0.04477 LP)
"""
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path('/srv/farm/ws')
DIR = ROOT / 'scratch/trial-dfm-pegkeeper-arbitrum'
BOTDIR = ROOT / 'bots/paper/trial-dfm-pegkeeper-arbitrum'
ARTIFACT = 'scratch/trial-dfm-pegkeeper-arbitrum/contracts/out/StepArb.sol/StepArb.json'
CAST = '/opt/foundry/bin/cast'
URL = 'http://127.0.0.1:9002'
CHAIN = 'arbitrum'
OWNER = '0xc0ffee0000000000000000000000000000000321'
STRANGER = '0xc0ffee0000000000000000000000000000000322'
PARENT = int(sys.argv[1]) if len(sys.argv) > 1 else 526250482
OUT = sys.argv[2] if len(sys.argv) > 2 else f'proof-result-{PARENT}.json'
GAS = 4_000_000
GASPRICE = 2 * 10**7

os.environ.setdefault('RPC_RELAY_URL', 'http://127.0.0.1:8545')
os.environ['BOT_MODE'] = 'paper'
spec = importlib.util.spec_from_file_location('bot', str(BOTDIR / 'bot.py'))
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)
ROUTE = 'usdt'
PK, POOL, IDX, COIN, FEE = bot.ROUTES[ROUTE]
TOKENS = {'usdc': bot.USDC, 'usdt': bot.USDT, 'lp': POOL}
ALLOW = [('usdc', bot.MORPHO), ('usdt', bot.UNIV3)]


def run(*args, check=True):
    p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=400)
    if p.returncode and check:
        raise RuntimeError(f'{args[:4]}: {p.returncode}: {p.stdout[-400:]} {p.stderr[-400:]}')
    return p.stdout.strip() if not p.returncode else None


def send(frm, to, data, gas=GAS):
    tx = {'from': frm, 'to': to, 'data': data, 'gas': hex(gas), 'gasPrice': hex(GASPRICE)}
    (DIR / 'last-tx.json').write_text(json.dumps(tx))
    raw = run('fork', 'send', CHAIN, json.dumps(tx))
    time.sleep(0.5)
    return json.JSONDecoder().raw_decode(raw[raw.index('{'):])[0]


def native(a):
    return int(run(CAST, 'balance', a, '--rpc-url', URL))


def bal(token, a):
    return int(run(CAST, 'call', token, 'balanceOf(address)(uint256)', a, '--rpc-url', URL).split()[0])


def allowance(token, o, s):
    return int(run(CAST, 'call', token, 'allowance(address,address)(uint256)', o, s, '--rpc-url', URL).split()[0])


def revert_output(h):
    return json.loads(run('fork', 'trace', CHAIN, h)).get('output')


def rc(r):
    return {'hash': r['transactionHash'], 'block': int(r['blockNumber'], 16), 'gas_used': int(r['gasUsed'], 16), 'status': r['status']}


def probe(addr, frm):
    data = bot.probe_calldata([bot.take_calldata(ROUTE, 1, addr)])
    p = subprocess.run([CAST, 'call', addr, data, '--from', frm, '--gas-limit', '100000000', '--rpc-url', URL, '--rpc-timeout', '300'],
                       cwd=ROOT, text=True, capture_output=True, timeout=400)
    if p.returncode:
        return None
    res = p.stdout.strip()
    words = [int(res[2 + i:2 + i + 64], 16) for i in range(0, len(res) - 2, 64)]
    return words[2]


run('fork', 'lease', CHAIN, '15', 'trial-dfm-pegkeeper-arbitrum-proof')
try:
    run('fork', 'reset', CHAIN, str(PARENT))
    enc = run(CAST, 'abi-encode', 'constructor(address)', OWNER)
    dep = run('fork', 'deploy', CHAIN, ARTIFACT, '--args', enc)
    addr = re.search(r'0x[0-9a-fA-F]{40}', dep).group(0)
    run('fork', 'fund', CHAIN, OWNER, '1')
    run('fork', 'fund', CHAIN, STRANGER, '1')
    result = {'reset_parent_block': PARENT, 'deployed': addr, 'deploy_output': dep[-300:], 'gas_price_wei': GASPRICE, 'route': ROUTE}
    gain = probe(addr, OWNER)
    result['probe_usdc'] = gain
    result['probe_from_stranger'] = 'reverts' if probe(addr, STRANGER) is None else 'ANSWERS'
    print('probe usdc', gain, flush=True)
    u0, n0 = bal(bot.USDC, OWNER), native(OWNER)
    nonowner = send(STRANGER, addr, bot.take_calldata(ROUTE, 1, addr))
    no_out = revert_output(nonowner['transactionHash'])
    assert nonowner['status'] == '0x0' and no_out == '0x30cd7471', f'NotOwner expected {no_out}'
    result['nonowner'] = dict(rc(nonowner), revert='NotOwner() 0x30cd7471')
    guard = send(OWNER, addr, bot.take_calldata(ROUTE, 10**24, addr))
    gout = revert_output(guard['transactionHash'])
    assert guard['status'] == '0x0' and gout.startswith('0x31708d59'), f'NoProfit expected {gout}'
    u1, n1 = bal(bot.USDC, OWNER), native(OWNER)
    result['guard'] = dict(rc(guard), min_profit=10**24, revert=gout[:140], owner_usdc_delta=u1 - u0, owner_native_delta_wei=n1 - n0)
    if not gain:
        result['success'] = None
        result['note'] = 'nothing to take at this block: the probe is 0'
    else:
        good = bot.take_calldata(ROUTE, gain // 2, addr)
        result['estimated_gas'] = int(run(CAST, 'estimate', addr, good, '--from', OWNER, '--rpc-url', URL))
        succ = send(OWNER, addr, good)
        u2, n2 = bal(bot.USDC, OWNER), native(OWNER)
        if succ['status'] != '0x1':
            (DIR / f'fail-trace-{PARENT}.json').write_text(run('fork', 'trace', CHAIN, succ['transactionHash']))
        gas_cost = int(succ['gasUsed'], 16) * int(succ.get('effectiveGasPrice', hex(GASPRICE)), 16)
        result['success'] = dict(rc(succ), min_profit=gain // 2, owner_usdc_delta=u2 - u1, owner_native_delta_wei=n2 - n1,
                                 gas_cost_wei=gas_cost)
        assert succ['status'] == '0x1' and u2 - u1 >= gain // 2, 'no gain'
        # the same call again right away: the regulator's 30 s action delay is running, nothing to take -> revert
        again = send(OWNER, addr, bot.take_calldata(ROUTE, 1, addr))
        u3 = bal(bot.USDC, OWNER)
        result['repeat'] = dict(rc(again), owner_usdc_delta=u3 - u2,
                                revert_output=(revert_output(again['transactionHash']) or '')[:330] if again['status'] == '0x0' else None)
        assert again['status'] == '0x0', 'repeat inside the action delay must revert'
        result['probe_after'] = probe(addr, OWNER)
    result['executor_leftovers'] = dict({'native': native(addr)}, **{k: bal(t, addr) for k, t in TOKENS.items()})
    result['executor_allowances'] = {f'{k}->{s}': allowance(TOKENS[k], addr, s) for k, s in ALLOW}
    result['owner_token_dust'] = {k: bal(t, OWNER) for k, t in TOKENS.items() if k != 'usdc'}
    code = run(CAST, 'code', addr, '--rpc-url', URL)
    (DIR / 'executor-runtime.hex').write_text(code + '\n')
    (DIR / OUT).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
finally:
    run('fork', 'release', CHAIN, check=False)
