import json
import subprocess

START, END = 26430488, 26480731
CONTRACTS = {
    "BridgeChef": "0xfb9108B960502D7B827Df29391008cdF657E1569",
    "LiquidityMiningPools": "0x306fD816e0DeED33439Eb495F1857E1727A869D8",
    "BuyBackAndBurn": "0x28576b9810988BA806F00A5fb4c318111A26b143",
}


def rpc(method, params):
    result = subprocess.run(
        ["python3", "/srv/farm/ws/tools/rpc.py", "ethereum", method, json.dumps(params)],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    if result.returncode or "error" in data:
        raise RuntimeError(f"{method}: {data.get('error')} {result.stderr}")
    return data["result"]


for name, address in CONTRACTS.items():
    code = rpc("eth_getCode", [address, "latest"])
    paused = rpc("eth_call", [{"to": address, "data": "0x5c975abb"}, "latest"])
    print(json.dumps({"name": name, "address": address, "code_bytes": (len(code)-2)//2, "paused": int(paused,16)}), flush=True)

for start in range(START, END+1, 8000):
    end = min(start+7999, END)
    for name in ("BridgeChef", "LiquidityMiningPools"):
        address = CONTRACTS[name]
        logs = rpc("eth_getLogs", [{"address":address, "fromBlock":hex(start), "toBlock":hex(end)}])
        print(json.dumps({"name":name,"from":start,"to":end,"count":len(logs),"topics":sorted(set(x["topics"][0] for x in logs))}),flush=True)
