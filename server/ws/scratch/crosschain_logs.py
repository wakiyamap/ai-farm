import json
import subprocess

START = 26430488
END = 26480731
BRIDGE = "0xCBCe172d7af2616804ab5b2494102dAeC47B2635"
REWARD = "0x0BDC1f983bC82B8F6F6BCcbF9810A9cdC1FE455f"
USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def logs(address, start, end):
    query = {"address": address, "fromBlock": hex(start), "toBlock": hex(end)}
    result = subprocess.run(
        ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "eth_getLogs", json.dumps([query])],
        text=True, capture_output=True,
    )
    data = json.loads(result.stdout)
    if result.returncode or "error" in data:
        raise RuntimeError(f"{start}-{end}: {data.get('error')} / {result.stderr}")
    return data["result"]


for address in (BRIDGE, REWARD):
    total = 0
    sample = []
    for start in range(START, END + 1, 8000):
        end = min(start + 7999, END)
        batch = logs(address, start, end)
        total += len(batch)
        sample.extend((e["transactionHash"], e["topics"][0]) for e in batch[:2])
        print(json.dumps({"address": address, "from": start, "to": end, "count": len(batch)}), flush=True)
    print(json.dumps({"address": address, "total": total, "sample": sample[:5]}), flush=True)

control = logs(USDC, END - 4, END)
print(json.dumps({"control": USDC, "from": END - 4, "to": END, "count": len(control), "first_tx": control[0]["transactionHash"] if control else None}), flush=True)
