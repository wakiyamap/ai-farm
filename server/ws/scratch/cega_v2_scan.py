import datetime
import json
import subprocess


def rpc(method, params):
    p = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", method, json.dumps(params)], capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    v = json.loads(p.stdout)
    if "error" in v:
        raise RuntimeError(v["error"])
    return v["result"]


head = rpc("eth_getBlockByNumber", ["latest", False])
head_number = int(head["number"], 16)
target = int(head["timestamp"], 16) - 7*86400
lo, hi = head_number - 100000, head_number
while lo + 1 < hi:
    mid = (lo + hi) // 2
    block = rpc("eth_getBlockByNumber", [hex(mid), False])
    if int(block["timestamp"], 16) < target:
        lo = mid
    else:
        hi = mid
start = rpc("eth_getBlockByNumber", [hex(hi), False])
print(json.dumps({"start": [hi, datetime.datetime.fromtimestamp(int(start["timestamp"],16), datetime.UTC).isoformat()], "head": [head_number, datetime.datetime.fromtimestamp(int(head["timestamp"],16), datetime.UTC).isoformat()]}), flush=True)
for name, addr in [("treasury", "0xA8AB795731fbBFDd1Fbc57ca11e6f722e7783642"), ("entry", "0x7a67d5eb2d6684d3e899575aaaa5ab31b79890c2"), ("manager", "0x1ddf7c4c98a78b492bb4a2881358f183d94c9806"), ("redeposit", "0xf8a62c2ed5588df7aba4713f79b4b4af56feb8f4")]:
    logs = rpc("eth_getLogs", [{"fromBlock": hex(hi), "toBlock": hex(head_number), "address": addr}])
    print(json.dumps({"name": name, "logs": len(logs), "sample": logs[:2]}), flush=True)
# Same-shape, no-topic known-active USDC contract over the final 100 blocks.
control = rpc("eth_getLogs", [{"fromBlock": hex(head_number-100), "toBlock": hex(head_number), "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"}])
print(json.dumps({"control_usdc_logs_last_100_blocks": len(control)}), flush=True)
