import json, sys, urllib.request, os
url = os.environ["RPC_RELAY_URL"]
def call(to, data, block="latest", chain="ethereum", lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},block]}).encode()
    req = urllib.request.Request(f"{url}/{chain}?lane={lane}", data=body, headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
    if "error" in r: return ("ERR", r["error"])
    return ("OK", r["result"])
if __name__ == "__main__":
    to, data = sys.argv[1], sys.argv[2]
    print(call(to, data))
