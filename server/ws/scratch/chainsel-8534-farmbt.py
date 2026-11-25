import json, subprocess, sys
RPC = '/srv/farm/ws/tools/rpc.py'
def call(ch, m, p):
    o = subprocess.run(['python3', RPC, ch, m, json.dumps(p), '--lane', 'research'], capture_output=True, text=True, timeout=60)
    return json.loads(o.stdout)['result']
for ch in sys.argv[1:]:
    try:
        b1 = call(ch, 'eth_getBlockByNumber', ['latest', False])
        h = int(b1['number'], 16); n = 2000
        b0 = call(ch, 'eth_getBlockByNumber', [hex(h - n), False])
        print(f"{ch} head={h} avg_block_s={(int(b1['timestamp'],16)-int(b0['timestamp'],16))/n:.3f} over {n} blocks")
    except Exception as e:
        print(ch, 'ERR', str(e)[:120])
