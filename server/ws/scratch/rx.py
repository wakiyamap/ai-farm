import subprocess, json
def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum",method,json.dumps(params)],
                       capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except Exception:
        print("RAW", r.stdout[:300], r.stderr[:200]); return None
    if "error" in d:
        print("ERR", d["error"]); return None
    return d["result"]

for name,h in [("market_cancel","0xbc03632f7b470be76ab5e741e63e650895a4cdbfefbe949eca9db5e5b37685bc"),
               ("staking_claim","0xb80a318f5bb7af94d55129c0fc299db00767d70c6618a2c51e0ca5c70be04be0")]:
    rec = rpc("eth_getTransactionReceipt",[h])
    if rec:
        print(name, "status", rec["status"], "gasUsed", int(rec["gasUsed"],16),
              [(l["topics"][0], [t[2:10] for t in l["topics"][1:]]) for l in rec["logs"]][:3])
