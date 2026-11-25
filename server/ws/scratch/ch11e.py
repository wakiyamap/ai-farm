import json, os, urllib.request, datetime
RELAY = os.environ["RPC_RELAY_URL"]
def rpc(method, params, lane="research"):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req = urllib.request.Request("%s/ethereum?lane=%s" % (RELAY, lane), data=body, headers={"content-type":"application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read())
    if "error" in d: raise SystemExit("ERR %s: %s" % (method, d["error"]))
    return d["result"]
tx = rpc("eth_getTransactionByHash",["0x4451f1725fb782368e9330c55929234a2f1d9ba2581528b555fb1a49594c0906"])
start_ts = 1794538031  # ChallengeStarted num11
exp = start_ts + 86400
win_ts = 1794630167
print("winner from:", tx["from"])
print("to:", tx["to"])
print("start:", datetime.datetime.utcfromtimestamp(start_ts), "expiry:", datetime.datetime.utcfromtimestamp(exp))
print("win:", datetime.datetime.utcfromtimestamp(win_ts), "win-expiry(h):", (win_ts-exp)/3600.0)
# winning bid word2 = 0x51ad2654f4a7f29b2aa
print("bid raw:", int("51ad2654f4a7f29b2aa",16))
# was there a tx to hub between expiry and win? count hub txs in blocks 26409800-26410802 via logs is not enough; check winner history in ledger
