import subprocess, json
# who else liquidates market 0x9103c3b4e8...? scan last ~700k blocks (~1.6d) topic0+topic1=market
params=[{"address":"0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb","fromBlock":hex(59400000),"toBlock":"latest","topics":["0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41","0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836"]}]
r=subprocess.run(['python3','tools/rpc.py','base','eth_getLogs',json.dumps(params)],capture_output=True,text=True)
try:
    logs=json.loads(r.stdout)['result']
except Exception:
    print("ERR",r.stdout[:200],r.stderr[:150]); raise SystemExit
print("logs:",len(logs))
from collections import Counter
c=Counter('0x'+l['topics'][2][-40:] for l in logs)
for k,v in c.most_common(10): print(k,v)
