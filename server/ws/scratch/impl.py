import json, urllib.request, os
URL=os.environ["RPC_RELAY_URL"]; LANE=os.environ.get("RPC_LANE","research")
def call(method, params):
    body={"jsonrpc":"2.0","id":1,"method":method,"params":params}
    r=urllib.request.urlopen(URL.rstrip("/")+"/ethereum?lane="+LANE, json.dumps(body).encode(), timeout=30)
    j=json.loads(r.read())
    if "error" in j: return {"error": j["error"]}
    return j["result"]
POOL="0xf1f53912c156a8c06927746cb20ba11ecec526ce"
slot="0x360894a13ba1a3210667c828492db98dca3f2018c555679e7f7ef85c0000000000000003"  # EIP1967 impl? standard slot 0x3606..99? use canonical:
impl=call("eth_getStorageAt",[POOL,"0x360894a13ba1a3210667c828492db98dca3f2018c555679e7f7ef85c0000000000000000","latest"])
print("impl slot raw:", impl)
for s in ["0x00000000000000000000000000000000000000000000000000000000000000a9"]:
    print("slot a9:", call("eth_getStorageAt",[POOL,s,"latest"]))
