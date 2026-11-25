import json, subprocess

RPC = "/srv/farm/ws/tools/rpc.py"


def call(method, params):
    o = subprocess.run(["python3", RPC, "ethereum", method, json.dumps(params), "--lane", "research"],
                       capture_output=True, text=True).stdout
    return json.loads(o).get("result")


d = json.load(open("/srv/farm/ws/scratch/lt-493c-adapter.json"))
d = d.get("result", d)
seen = set()
for l in d:
    if l["topics"][0].startswith("0xf4abeb4e") and l["transactionHash"] not in seen:
        seen.add(l["transactionHash"])
        t = call("eth_getTransactionByHash", [l["transactionHash"]])
        print(int(l["blockNumber"], 16), t["from"], t["to"], t["input"][:10], l["transactionHash"])
r = call("eth_call", [{"to": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419", "data": "0x50d25bcd"}, "latest"])
print("ETHUSD", int(r, 16) / 1e8)
