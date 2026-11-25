import json, sys, urllib.request
net, lch = sys.argv[1], sys.argv[2]
toks = sys.argv[3:]
URL = f"https://subgraph-endpoints.superfluid.dev/{net}/protocol-v1"
def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", "user-agent": "curl/8"})
    return json.load(urllib.request.urlopen(req, timeout=40))
def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"user-agent": "curl/8"}), timeout=40))
r = post(URL, {"query": '{ tokens(where: {id_in: %s}) { id symbol name isListed isSuperToken underlyingAddress underlyingToken { symbol name } } }' % json.dumps(toks)})
for t in r["data"]["tokens"]:
    print(t)
    ks = [f"{lch}:{t['id']}"] + ([f"{lch}:{t['underlyingAddress']}"] if t["underlyingAddress"] and int(t["underlyingAddress"], 16) else [])
    print("   price", get("https://coins.llama.fi/prices/current/" + ",".join(ks))["coins"])
