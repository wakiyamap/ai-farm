import json, subprocess
FB, TB = "0x19302bf", "0x193c72b"
T0 = "0x442e715f626346e8c52d060c327f2b66ae193aff123b0d5294f208b4019d369d"  # from receipt of 0x0d63c9...
def logs(params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_getLogs",json.dumps(params)],
                       capture_output=True, text=True)
    try: return json.loads(r.stdout)["result"]
    except Exception: return {"ERR": r.stdout[:200]+r.stderr[:200]}
safes = ["0xBE6297731720B7E218031Ca8970921f9b41f3D00","0xAd713bd85E8bff9CE85Ca03a8A930e4a38f6893D","0x9bc8ef6bb09e3d0f3f3a6cd02d2b9dc3115c7c5c"]
res = logs([{"fromBlock":FB,"toBlock":TB,"address":safes,"topics":[T0]}])
print("ExecutionSuccess 7d count:", len(res) if isinstance(res,list) else res)
if isinstance(res,list):
    for lg in res:
        print(" ", lg["address"], int(lg["blockNumber"],16), lg["transactionHash"])
# isOwner check + execTransaction refund fields
def call(to,data):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_call",json.dumps([{ "to":to,"data":data},"latest"])],
                       capture_output=True, text=True)
    return json.loads(r.stdout).get("result")
sel = "0x8f283b3c"  # isOwner(address)
print("isOwner(e1bb) on ad71:", call("0xAd713bd85E8bff9CE85Ca03a8A930e4a38f6893D", sel+"000000000000000000000000e1bb4b59a75c41e343c089b90e41dfa15d020acd"))
print("isOwner(57bb) on ad71:", call("0xAd713bd85E8bff9CE85Ca03a8A930e4a38f6893D", sel+"00000000000000000000000057bb6a8563a8e8478391c79f3f433c6ba077c567"))
