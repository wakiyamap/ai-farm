import json, subprocess, collections

RPC = ['python3', '/srv/farm/ws/tools/rpc.py', 'avalanche']
def call(method, params):
    out = subprocess.run(RPC + [method, json.dumps(params)], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f'{method} failed: {out.stderr[:300]}')
    return json.loads(out.stdout)['result']

head = int(call('eth_blockNumber', []), 16)
head_ts = int(call('eth_getBlockByNumber', [hex(head), False])['timestamp'], 16)
print('head', head, 'ts', head_ts)

ADDRS = ["0xcF0fa4c193006Ac3b4dEAF8729f531988C72201A","0xe54dD8197aa2746C23Fa2db50E0b9eC5B8A154eF",
"0x14Eb29bb4F2d90A3B413cc06Acc579f628250bFC","0x7Af0333eCf703bfBd5aeC24777B8cEE03517e603",
"0xD66278CE88b842368811053EE68a3e3Ead3fBbd3","0x51c9F9983e5b34B9F04bfDde517730043A4C2C28",
"0x038e5A1141F3f79265251591254c15eB4016FFFA","0x7DAF18e680f00143ae37B56cB3E95c97F67D9d08",
"0x5916366020A0054786EFe9Ed81a65B849b185e94","0xFe458CD6d4C9C3EB49566A064f6335B74bFD7FB2"]
TOPIC = "0xd255b592c7f268a73e534da5219a60ff911b4cf6daae21c7d20527dd657bd99a"

start = head - 620000  # ~7 days at ~1 block/s
logs = []
pages = 0
b = start
while b <= head:
    e = min(b + 9500, head)
    ls = call('eth_getLogs', [{"fromBlock": hex(b), "toBlock": hex(e), "address": ADDRS, "topics": [TOPIC]}])
    logs += ls
    pages += 1
    b = e + 1
txs = set(l['transactionHash'] for l in logs)
em = set(l['address'].lower() for l in logs)
print(f'7d scan: {pages} pages, {len(logs)} ChargedFees events, {len(txs)} txs, {len(em)} emitters')
ts = {}
for l in logs:
    ts[l['address'].lower()] = ts.get(l['address'].lower(), 0) + 1
for a, c in sorted(ts.items()):
    print(' emitter', a, c)
# save logs for sample selection
json.dump(logs, open('scratch/beefy-avax-scout-logs.json', 'w'))

# want() getter on one strategy
w = call('eth_call', [{"to": "0x51c9F9983e5b34B9F04bfDde517730043A4C2C28", "data": "0x1f1fcd51"}, "latest"])
print('want() ->', w)

# stranger harvest(address) eth_call from fresh address, latest and at winner block 100507152
STRANGER = "0x000000000000000000000000000000000000bEEf"
data = "0x0e5c011e" + STRANGER[2:].zfill(64)
for blk in ["latest", "0x5FF1A50"]:
    try:
        r = call('eth_call', [{"from": STRANGER, "to": "0x51c9F9983e5b34B9F04bfDde517730043A4C2C28", "data": data}, blk])
        print(f'harvest(address) stranger @{blk}: OK result={r}')
    except Exception as ex:
        print(f'harvest(address) stranger @{blk}: {str(ex)[:200]}')
