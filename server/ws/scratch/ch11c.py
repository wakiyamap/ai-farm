import json, os, urllib.request, subprocess
RELAY = os.environ["RPC_RELAY_URL"]
HUB = "0xDE12B620A8a714476A97EfD14E6F7180Ca653557"
POS = "0xda2fc6cdb14792ca763f853e2db3da007db42099"
def rpc(method, params, lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request("%s/ethereum?lane=%s" % (RELAY, lane), data=body, headers={"content-type":"application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=90).read())
    if "error" in d: raise SystemExit("ERR %s: %s" % (method, d["error"]))
    return d["result"]
def s4(sel): return subprocess.run(["/opt/foundry/bin/cast","keccak",sel],capture_output=True,text=True).stdout.strip()[:10]
def call(to, data, block="latest"):
    return rpc("eth_call", [{"to":to,"data":data}, block])
head = int(rpc("eth_blockNumber",[]),16)
print("head", head)
ok = call("0x0998371bef13a848ba188337031839a1257d4ab7", s4("challengeData()"), "0x191c5c3")
print("control num8 challengeData@26293523:", ok[:132])
cd = call(POS, s4("challengeData()"), "latest")
print("num11 challengeData@head:", cd)
w = [int(cd[2+i:66+i],16) for i in range(0,max(0,len(cd)-2),64)]
print("num11 words:", w)
logs = rpc("eth_getLogs",[{"address":HUB,"fromBlock":26403144,"toBlock":head}])
print("hub logs since start:", len(logs))
for e in logs[:40]:
    t0 = e["topics"][0][2:10] if e.get("topics") else ""
    print(int(e["blockNumber"],16), t0, e["transactionHash"][:20])
