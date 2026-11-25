import json, subprocess
STRAT = "0x2fb611faf48b1d1b91edbba34cee10c6357adee410540e4a8f7a82b6b38673e4"
TT = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
latest = 0x9860ef3
FR = latest - 45*7*7200
def gl(addr, topic):
    p = ["python3","/srv/farm/ws/tools/rpc.py","optimism","eth_getLogs",
         json.dumps([{"address":addr,"topics":[topic],"fromBlock":hex(FR),"toBlock":hex(latest)}])]
    out = subprocess.run(p, capture_output=True, text=True)
    if out.returncode != 0: print("ERR", out.stderr[:200]); return None
    return json.loads(out.stdout)["result"]
for a in ["0xf7D66b41Cd4241eae450fd9D2d6995754634D9f3","0xd0d2Ac44Cc842079e978bB11b094764f7D0dec6A"]:
    r = gl(a, STRAT)
    print(a, "StrategyReported 45d:", None if r is None else len(r))
    if r:
        for l in r[-4:]: print("   blk", int(l["blockNumber"],16), l["transactionHash"])
    c = gl(a, TT)
    print("   control Transfer 45d:", None if c is None else len(c))
