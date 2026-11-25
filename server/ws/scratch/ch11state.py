import json, os, urllib.request, subprocess
RELAY = os.environ["RPC_RELAY_URL"]
HUB = "0xDE12B620A8a714476A97EfD14E6F7180Ca653557"
POS = "0xda2fc6cdb14792ca763f853e2db3da007db42099"
def rpc(method, params, lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request("%s/ethereum?lane=%s" % (RELAY, lane), data=body, headers={"content-type":"application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read())
    if "error" in d: raise SystemExit("ERR %s: %s" % (method, d["error"]))
    return d["result"]
def s4(sel): return subprocess.run(["/opt/foundry/bin/cast","keccak",sel],capture_output=True,text=True).stdout.strip()[:10]
def call(to, sigs, args_hex="", block="latest"):
    return rpc("eth_call", [{"to": to, "data": s4(sigs) + args_hex}, block])
head = int(rpc("eth_blockNumber",[]),16)
print("head", head)
cd = call(HUB, "challengeData(bytes32)", POS[2:].rjust(64,"0"))
print("challengeData latest:", cd)
words = [cd[2+i:66+i] for i in range(0, max(0,len(cd)-2), 64)]
print("words:", [w if int(w,16)!=0 else "0" for w in words])
logs = rpc("eth_getLogs",[{"address":HUB,"fromBlock":26403144,"toBlock":head}])
print("hub logs since start:", len(logs))
for e in logs[:30]:
    t0 = e["topics"][0][2:10] if e.get("topics") else ""
    print(e["blockNumber"], t0, e["transactionHash"][:18])
