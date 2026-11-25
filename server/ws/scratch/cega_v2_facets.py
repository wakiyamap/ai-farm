import json
import pathlib
import subprocess
import time

p = subprocess.run(["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "eth_call", '[{"to":"0x7a67d5eb2d6684d3e899575aaaa5ab31b79890c2","data":"0x52ef6b2c"},"latest"]'], capture_output=True, text=True, check=True)
data = json.loads(p.stdout)["result"][2:]
count = int(data[64:128], 16)
print("count", count, flush=True)
for i in range(count):
    address = "0x" + data[128+i*64+24:128+(i+1)*64]
    path = pathlib.Path(f"scratch/cega_v2_facet_{i+1}")
    if path.exists():
        files = list(path.rglob("*.sol"))
        if files:
            print(i+1, address, "cached", [p.name for p in files if p.name.endswith("Entry.sol")][:3], flush=True)
            continue
    p = subprocess.run(["explorer", "source", "ethereum", address, "--out", str(path)], capture_output=True, text=True)
    name = next((line for line in p.stdout.splitlines() if line.startswith("name:")), p.stderr.strip() or p.stdout.strip())
    print(i+1, address, name, flush=True)
    time.sleep(0.6)
