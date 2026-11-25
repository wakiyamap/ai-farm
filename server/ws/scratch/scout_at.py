import json, subprocess, sys
ADDR="0x302649ccdfc232ee49a28755c8a6c06e707b7d15"
def rpc(method, params):
    out = subprocess.run(["python3","tools/rpc.py","base",method,json.dumps(params),"--lane","research"],
                         capture_output=True, text=True).stdout
    return json.loads(out)["result"]
for b in sys.argv[1:]:
    bn = hex(int(b, 0))
    r = rpc("alchemy_getAssetTransfers", [{"fromBlock":bn,"toBlock":bn,"fromAddress":ADDR,"toAddress":ADDR,
        "order":"desc","pageSize":"0x3e8","withMetadata":False,"excludeFailedTransfers":True}])
    print("== block", int(b,0), "transfers touching addr:", len(r["transfers"]))
    for t in r["transfers"]:
        print("  ", t["hash"][:14], t["rawContract"]["address"][:12], t["from"][:10],"->",t["to"][:10], t.get("asset"), int(t["rawValue"],16), t.get("tokenStandard"))
