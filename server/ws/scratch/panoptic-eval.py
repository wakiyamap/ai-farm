import json
import subprocess

POOL = "0x00000000000e98f6c5ae16835badf2f7cc0d49d7"
FRESH = "0x1111111111111111111111111111111111111111"
trace = json.load(open("scratch/panoptic-trace.json"))

def find_dispatch(node):
    if node.get("to", "").lower() == POOL.lower() and node.get("input", "").startswith("0x4c2de0f9"):
        return node["input"]
    for child in node.get("calls", []):
        found = find_dispatch(child)
        if found:
            return found

data = find_dispatch(trace)
assert data and len(data) == 586
open("scratch/panoptic-dispatch-calldata.hex", "w").write(data + "\n")

def run(label, args):
    result = subprocess.run(args, capture_output=True, text=True)
    print(label, "exit", result.returncode, "stdout", result.stdout[:1000], "stderr", result.stderr[:1000])

run("direct_before_poke", ["fork", "call", "ethereum", json.dumps({"from": FRESH, "to": POOL, "data": data})])
run("poke", ["fork", "send", "ethereum", json.dumps({"from": FRESH, "to": POOL, "data": "0x48c707c4", "gas": "0x1e8480"})])
run("direct_after_poke", ["fork", "call", "ethereum", json.dumps({"from": FRESH, "to": POOL, "data": data})])
