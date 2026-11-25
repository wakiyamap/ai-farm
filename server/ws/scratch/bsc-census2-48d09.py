import json, os, time, urllib.request, collections

URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                d = json.loads(r.read())
            if "error" in d:
                time.sleep(1); continue
            return d["result"]
        except Exception:
            time.sleep(2)
    return None

USDT="0x55d398326f99059ff775485246999027b3197955"
WBNB="0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
USDC="0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
T0="0x"+"ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
head=int(rpc("eth_blockNumber"),16)
PAGES=12; PAGE=250
send=collections.Counter(); recv=collections.Counter(); tok=collections.Counter()
per_page=[]; ok_logs=0
addrset={USDT:"USDT",WBNB:"WBNB",USDC:"USDC18"}
for i in range(PAGES):
    a=head-PAGE*(i+1); b=a+PAGE-1
    logs=rpc("eth_getLogs",[{"topics":[T0],"fromBlock":hex(a),"toBlock":hex(b)}])
    if logs is None:
        per_page.append((a,"ERR")); continue
    per_page.append((a,len(logs)))
    ok_logs+=len(logs)
    for L in logs:
        tok[addrset.get(L["address"],L["address"])]+=1
        if len(L["topics"])>=3:
            send[L["topics"][1][10:46].lower()]+=1
            recv[L["topics"][2][10:46].lower()]+=1
    time.sleep(0.2)
out={"head":head,"blocks_covered":PAGE,"pages":per_page,"ok_logs":ok_logs,
     "top_tokens":tok.most_common(15),"top_senders":send.most_common(20),"top_receivers":recv.most_common(20)}
json.dump(out, open("scratch/bsc-census2-48d09.json","w"))
print("head",head,"ok_logs",ok_logs)
print("tokens:", out["top_tokens"][:10])
print("senders:")
for a,c in out["top_senders"]: print(a,c)
