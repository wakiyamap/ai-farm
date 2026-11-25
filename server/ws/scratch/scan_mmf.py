import subprocess, json, sys
vaults = open('scratch/chamber-vaults-op-nz.txt').read().split()
topic = '0x755a8059d66d8d243bc9f6913f429a811f154599d0538bb0b6a2ac23f23d2ccd'
FR, TO = 159476513, 159778913
logs = []
for i in range(0, len(vaults), 32):
    batch = vaults[i:i+32]
    params = json.dumps([{"fromBlock": hex(FR), "toBlock": hex(TO),
                          "address": batch, "topics": [topic]}])
    r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','optimism','eth_getLogs',params],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print('ERR batch', i, r.stderr[:200]); sys.exit(1)
    out = json.loads(r.stdout)
    logs += out['result']
print('total ManagerFeeMinted 7d:', len(logs))
from collections import Counter
c = Counter(l['address'].lower() for l in logs)
print('distinct emitting vaults:', len(c))
for a, n in c.most_common(10): print(a, n)
json.dump(logs, open('scratch/mmf_logs.json','w'))
