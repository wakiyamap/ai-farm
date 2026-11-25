import json
import subprocess

ADDR = "0xab37e1358b639fd877f015027bb62d3ddaa7557e"
FRESH = "0x1111111111111111111111111111111111111111"


def command(args):
    return subprocess.run(args, capture_output=True, text=True)


for signature, args in [
    ("receiveDividend(address,address)", ["0x0000000000000000000000000000000000000000", FRESH]),
    ("settleProfit(address)", ["0x0000000000000000000000000000000000000000"]),
    ("unreceivedDividend(address,address)", ["0x0000000000000000000000000000000000000000", FRESH]),
]:
    calldata = command(["/opt/foundry/bin/cast", "calldata", signature, *args]).stdout.strip()
    call = command([
        "python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "eth_call",
        json.dumps([{"from": FRESH, "to": ADDR, "data": calldata}, "latest"]),
    ])
    print(json.dumps({"signature": signature, "data": calldata, "code": call.returncode, "response": call.stdout.strip(), "stderr": call.stderr.strip()}))
