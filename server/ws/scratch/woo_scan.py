#!/usr/bin/env python3
"""Scan BSC for ClaimReward events on WOOFi RebateManager over last 7 days (5000-block chunks)."""
import subprocess, json, sys, time

RPC = ['python3', '/srv/farm/ws/tools/rpc.py', 'bsc', 'eth_getLogs']
LANE = ['--lane', 'paper']
ADDR = '0x7616614084e040028D6a61c0f3A9699c121A6500'
TOPIC = '0xba8de60c3403ec381d1d484652ea1980e3c3e56359195c92525bff4ce47ad98e'  # ClaimReward(address,uint256)
HEAD = 134512702
START = 133169508  # head - 7d at 0.45 s/block

def getlogs(f, t):
    params = json.dumps([{"address": ADDR, "topics": [TOPIC],
                          "fromBlock": hex(f), "toBlock": hex(t)}])
    for attempt in range(6):
        out = subprocess.run(RPC + [params] + LANE, capture_output=True, text=True)
        try:
            d = json.loads(out.stdout)
            if 'result' in d:
                return d['result']
        except Exception:
            pass
        time.sleep(3 + attempt * 3)
    return None

found = []
errors = 0
f = START
with open('/srv/farm/ws/scratch/woo_scan.log', 'w') as log:
    while f <= HEAD:
        t = min(f + 4999, HEAD)
        r = getlogs(f, t)
        if r is None:
            errors += 1
            log.write(f"ERR {f}-{t}\n"); log.flush()
        else:
            for l in r:
                found.append({'block': int(l['blockNumber'], 16), 'tx': l['transactionHash'],
                              'broker': '0x' + l['topics'][1][-40:], 'raw': l['data']})
            if r:
                log.write(f"HIT {f}-{t}: {len(r)}\n"); log.flush()
        f = t + 1
        time.sleep(0.4)
    with open('/srv/farm/ws/scratch/woo_claimreward_7d.json', 'w') as o:
        json.dump({'found': found, 'errors': errors, 'chunks': (HEAD - START) // 5000 + 1}, o)
    log.write(f"DONE events={len(found)} errors={errors}\n")
