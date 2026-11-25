"""Value the liquidator-received Superfluid rewards: token symbol/underlying from the subgraph, price from coins.llama.fi.
usage: sf_value.py <network> <llama-chain>
"""
import json, sys, urllib.request

net, lch = sys.argv[1], sys.argv[2]
URL = f"https://subgraph-endpoints.superfluid.dev/{net}/protocol-v1"
rows = json.load(open(f"/srv/farm/ws/scratch/sf_sub_{net}.json"))


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json", "user-agent": "curl/8"})
    return json.load(urllib.request.urlopen(req, timeout=40))


def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"user-agent": "curl/8"}), timeout=40))


toks = sorted({e["token"] for e in rows})
r = post(URL, {"query": '{ tokens(where: {id_in: %s}) { id symbol decimals isNativeAssetSuperToken underlyingAddress underlyingToken { symbol decimals } } }' % json.dumps(toks)})
meta = {t["id"]: t for t in r["data"]["tokens"]}
keys = []
for t in meta.values():
    keys.append(f"{lch}:{t['id']}")
    if t["underlyingAddress"] and int(t["underlyingAddress"], 16):
        keys.append(f"{lch}:{t['underlyingAddress']}")
pr = get("https://coins.llama.fi/prices/current/" + ",".join(keys))["coins"]
native = get(f"https://coins.llama.fi/prices/current/coingecko:ethereum,coingecko:matic-network")["coins"]
print("native", {k: v["price"] for k, v in native.items()})
tot = 0
for e in rows:
    m = meta[e["token"]]
    got = e["rewardAmountReceiver"].lower() == e["liquidatorAccount"].lower()
    p = None
    if m["isNativeAssetSuperToken"]:
        p = native["coingecko:matic-network" if lch == "polygon" else "coingecko:ethereum"]["price"]
    for k in (f"{lch}:{m['underlyingAddress']}", f"{lch}:{m['id']}"):
        if p is None and k in pr:
            p = pr[k]["price"]
    amt = int(e["rewardAmount"]) / 1e18
    usd = amt * p if p is not None else None
    if got and usd:
        tot += usd
    print(e["timestamp"], e["blockNumber"], e["transactionHash"], m["symbol"], "type", e["liquidationType"], "liq", e["liquidatorAccount"][:10],
          "got" if got else "toPIC", "amt %.6g" % amt, "usd", ("%.4f" % usd) if usd is not None else "noprice", "gasUsed", e["gasUsed"], "gasPrice", e["gasPrice"])
print("total USD to liquidators (priced only): %.2f over %d events" % (tot, len(rows)))
