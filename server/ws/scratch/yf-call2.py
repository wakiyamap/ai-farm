import json, subprocess
S = "0x02e0e677fad4a8dc9007a7bed973bf0c70905929"
FRESH = "0x00000000000000000000000000000000000A11ce"
def call(data, frm=None):
    p = ["python3","/srv/farm/ws/tools/rpc.py","optimism","eth_call",
         json.dumps([{"to":S,"data":data,"from":frm} if frm else {"to":S,"data":data},"latest"])]
    out = subprocess.run(p, capture_output=True, text=True)
    return json.loads(out.stdout)
r = call("0x6c003a9b"); print("claimableRewards:", r.get("result"))
r = call("0xb5762114"); print("claimableProfitInUsdc:", r.get("result"))
r = call("0xaced1661"); print("keeper:", r.get("result"))
r = call("0x9ec5a894"); print("rewards:", r.get("result"))
r = call("0x4641257d", "0xc6387e937bcef8de3334f80edc623275d42457ff"); print("harvest from keeper EOA:", json.dumps(r)[:160])
# harvestTrigger(uint256) with a fake gas arg 500k
import struct
r = call("0x9f5e2177" + hex(500000)[2:].rjust(64,"0")); print("harvestTrigger(500k):", r.get("result"))
