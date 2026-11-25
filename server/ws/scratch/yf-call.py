import json, subprocess
S = "0x02e0e677fad4a8dc9007a7bed973bf0c70905929"
FRESH = "0x00000000000000000000000000000000000A11ce"
def call(data, frm=None):
    p = ["python3","/srv/farm/ws/tools/rpc.py","optimism","eth_call",
         json.dumps([{"to":S,"data":data,"from":frm} if frm else {"to":S,"data":data},"latest"])]
    out = subprocess.run(p, capture_output=True, text=True)
    try: return json.loads(out.stdout)
    except: return {"raw": out.stdout[:200], "err": out.stderr[:200]}
print("harvest() from stranger:", json.dumps(call("0x4641257d", FRESH))[:300])
for sel,name in [("0x282f8227","claimableRewards"),("0x259f7e74","claimableProfitInUsdc")]:
    pass
