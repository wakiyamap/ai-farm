"""Sample UniswapX fill receipts: per fill, net ERC20 flows of the filler address and of tx.from, gas used x price.
usage: chain n"""
import json, subprocess, sys, random, collections
chain, n = sys.argv[1], int(sys.argv[2])
TR = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
def rpc(m, p):
    r = subprocess.run(['python3', '/srv/farm/ws/tools/rpc.py', chain, m, json.dumps(p), '--lane', 'research'], capture_output=True, text=True)
    return json.loads(r.stdout)['result']
logs = json.load(open(f'/srv/farm/ws/scratch/uniswapx-2685-logs-{chain}.json'))
if isinstance(logs, dict): logs = logs.get('logs', logs.get('result', []))
random.seed(3)
samp = random.sample(logs, min(n, len(logs)))
for l in samp:
    filler = '0x' + l['topics'][2][-40:]; swapper = '0x' + l['topics'][3][-40:]
    rc = rpc('eth_getTransactionReceipt', [l['transactionHash']])
    tx = rpc('eth_getTransactionByHash', [l['transactionHash']])
    net = collections.defaultdict(lambda: collections.defaultdict(int))
    for x in rc['logs']:
        if x['topics'][0] == TR and len(x['topics']) == 3:
            a, f_, t_ = x['address'].lower(), '0x' + x['topics'][1][-40:], '0x' + x['topics'][2][-40:]
            v = int(x['data'], 16) if x['data'] != '0x' else 0
            for who in (filler, tx['from'].lower(), swapper):
                if f_ == who: net[who][a] -= v
                if t_ == who: net[who][a] += v
    gas = int(rc['gasUsed'], 16) * int(rc['effectiveGasPrice'], 16) / 1e18
    print(json.dumps({"tx": l['transactionHash'], "block": int(l['blockNumber'], 16), "idx": int(rc['transactionIndex'], 16), "from": tx['from'], "to": tx['to'],
                      "filler": filler, "gas_native": round(gas, 7), "prio_gwei": round((int(rc['effectiveGasPrice'], 16)) / 1e9, 4), "n_logs": len(rc['logs']),
                      "net": {k: {t: v for t, v in d.items() if v} for k, d in net.items()}}))
