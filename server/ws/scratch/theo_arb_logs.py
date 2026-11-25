import subprocess, json, time

def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","arbitrum",method,json.dumps(params)],
                       capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        return ("ERR", (r.stdout + r.stderr).strip()[:300])
    try: return ("OK", json.loads(r.stdout).get("result"))
    except Exception: return ("ERR", r.stdout[:300])

HEAD = 526599984
START7 = 524546479
A = "0x3ca8F12D7B376E9Ef338d1C432CA1b51DD319009"
st, logs = rpc("eth_getLogs", [{"address": A, "fromBlock": hex(START7), "toBlock": hex(HEAD)}])
for l in logs:
    print(json.dumps({"block": int(l["blockNumber"],16), "tx": l["transactionHash"], "topic0": l["topics"][0] if l["topics"] else None, "data": l["data"][:130], "idx": l["logIndex"]}))
