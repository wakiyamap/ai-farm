import json, subprocess
TOPIC_T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # Transfer
STRAT = "0x2fb611faf48b1d1b91edbba34cee10c6357adee410540e4a8f7a82b6b38673e4"
latest = 0x9860ef3
def gl(addrs, topic, fr, to=latest):
    p = ["python3","/srv/farm/ws/tools/rpc.py","optimism","eth_getLogs",
         json.dumps([{"address":addrs,"topics":[topic],"fromBlock":hex(fr),"toBlock":hex(to)}])]
    out = subprocess.run(p, capture_output=True, text=True)
    if out.returncode != 0: print("ERR", out.stderr[:200]); return None
    return json.loads(out.stdout)["result"]
# control: Transfer on top 2 vaults, last 24h (~43200 blocks)
r = gl(["0xf7D66b41Cd4241eae450fd9D2d6995754634D9f3","0xd0d2Ac44Cc842079e978bB11b094764f7D0dec6A"], TOPIC_T, latest-43200)
print("control Transfer 24h on 2 vaults:", None if r is None else len(r))
# 90d StrategyReported on top 32 vaults
addr = [v["address"] for v in json.load(open("scratch/yf-op-vaults.json"))]
for i in range(0,32,32):
    r = gl(addr[i:i+32], STRAT, latest-90*7*7200)
    print(f"90d StrategyReported vaults chunk{i//32}:", None if r is None else len(r))
    if r:
        import datetime
        for l in r[-5:]:
            print("  blk", int(l["blockNumber"],16), l["address"])
