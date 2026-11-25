import collections
import json
from pathlib import Path

transfer = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
actors = [
    "0x8ab5db84d241f4cca7de44d9f84d393f78b099f1",
    "0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd",
]
for i, actor in enumerate(actors, 1):
    receipt = json.loads(Path(f"scratch/llama-arb-receipt{i}.json").read_text())["result"]
    net = collections.Counter()
    for log in receipt["logs"]:
        if log["topics"][0] != transfer:
            continue
        source = "0x" + log["topics"][1][-40:]
        dest = "0x" + log["topics"][2][-40:]
        value = int(log["data"], 16)
        if source == actor:
            net[log["address"]] -= value
        if dest == actor:
            net[log["address"]] += value
        if source == actor or dest == actor:
            print(" transfer", log["address"], source, dest, value)
    print(i, dict(net))
