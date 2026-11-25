import json, subprocess
def logs(params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_getLogs",json.dumps(params)],
                       capture_output=True, text=True)
    try: return json.loads(r.stdout)["result"]
    except Exception: return {"ERR": r.stdout[:200]+r.stderr[:200]}
for a in ["0xBE6297731720B7E218031Ca8970921f9b41f3D00","0x9bc8ef6bb09e3d0f3f3a6cd02d2b9dc3115c7c5c"]:
    res = logs([{"fromBlock":"0x19302bf","toBlock":"0x193c72b","address":a}])
    print(a[:8], "no-topic scan 7d:", len(res) if isinstance(res,list) else res)
