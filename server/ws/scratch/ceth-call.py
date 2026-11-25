import json, sys, urllib.request
RELAY = "http://127.0.0.1:8545"
CETH = "0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5"
CHAIN = sys.argv[1] if len(sys.argv) > 1 else "ethereum"
lane = "lane=research"
def call(data, to=CETH):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"latest"]})
    req = urllib.request.Request(f"{RELAY}/{CHAIN}?{lane}", data=body.encode(), headers={"content-type":"application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=30))
    if "error" in r: return ("ERR", r["error"])
    return ("OK", r["result"])
sels = {
  "borrowRate": "0xc914b437",
  "utilizationRate": "0x6c321c8a",
  "reserveFactor": "0x4322b714",
  "totalBorrows": "0x47bd3718",
  "totalSupply": "0x18160ddd",
  "exchangeRateStored": "0x182df0f5",
  "supplyCap": "0x8f770ad0",
  "accrualBlockNumber": "0xdb006a75",  # placeholder, fixed below
}
import subprocess
s = subprocess.run(["cast","keccak","accrualBlockNumber()"],capture_output=True,text=True).stdout.strip()
sels["accrualBlockNumber"] = "0x"+s[:8]
for name, sel in sels.items():
    st, res = call(sel)
    if st == "OK":
        v = int(res, 16) if res != "0x" else None
        print(f"{name}: raw={res} -> {v}")
    else:
        print(f"{name}: {res}")
