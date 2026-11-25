import json, sys, urllib.request
RELAY = "http://127.0.0.1:8545"
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
def call(data, to=CETH):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"latest"]})
    req = urllib.request.Request(f"{RELAY}/ethereum?lane=research", data=body.encode(), headers={"content-type":"application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=30))
    if "error" in r: return ("ERR", r["error"].get("message") or r["error"])
    return ("OK", r["result"])
import subprocess
def sel(sig):
    k = subprocess.run(["cast","keccak",sig],capture_output=True,text=True).stdout.strip()
    return k[:10]
for name in ["mintGuardianPaused()", "mintIsPaused()", "pausedMint()", "redeemGuardianPaused()", "accrualBlockNumber()", "balanceOf(address)"]:
    s = sel(name)
    if name.startswith("balanceOf") or name.endswith("(address)"):
        data = s + "0"*24 + "d1f583bc0a7754d634bb12111399fa0308".lower()
    else:
        data = s
    st,res = call(data)
    print(name, s, st, res[:80] if isinstance(res,str) else res)
