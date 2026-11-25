import json
import subprocess

AGGS = [
    "0xE446158503d0F5c70579FCCE774C00E8Db544559",
    "0x5F3b6405dfcF8b21f8dEB4eb6DA44a89a652aCb0",
    "0xCc96397Cb86f98759BdbbF31802b366E7251F350",
]
FRESH = "0x1111111111111111111111111111111111111111"
for addr in AGGS:
    for name, data in [
        ("claimReward", "0xb88a802f"),
        ("getRewardAmount", "0x44a040f5" + "0" * 24 + FRESH[2:]),
        ("balanceOf", "0x70a08231" + "0" * 24 + FRESH[2:]),
        ("getInfo", "0x5a9b0b89"),
    ]:
        p = subprocess.run(
            ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", "eth_call", json.dumps([{"from": FRESH, "to": addr, "data": data}, "latest"])],
            capture_output=True,
            text=True,
        )
        print(json.dumps({"address": addr, "method": name, "response": json.loads(p.stdout).get("result", json.loads(p.stdout).get("error"))}))
