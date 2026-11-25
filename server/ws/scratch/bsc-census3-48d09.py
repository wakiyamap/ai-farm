import json, os, time, urllib.request, collections

URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(4):
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
PAGE=125; pages_ok=[]
send=collections.Counter(); recv=collections.Counter(); tok=collections.Counter()
pairs=collections.Counter()
addrset={USDT:"USDT",WBNB:"WBNB",USDC:"USDC18"}
total=0
for i in range(10):
    a=head-PAGE*(i+1); b=a+PAGE-1
    logs=rpc("eth_getLogs",[{"topics":[T0],"fromBlock":hex(a),"toBlock":hex(b)}])
    if logs is None:
        pages_ok.append((a,"ERR")); continue
    pages_ok.append((a,len(logs))); total+=len(logs)
    for L in logs:
        tok[addrset.get(L["address"],L["address"])]+=1
        if len(L["topics"])>=3:
            s=L["topics"][1][26:].lower(); r=L["topics"][2][26:].lower()
            send[s]+=1; recv[r]+=1
            pairs[(L["address"],s if s!=L["address"][-40:] else r)]+=1
    time.sleep(0.2)
def dec(c): return [("0x"+k,v) for k,v in c.most_common(25)]
out={"head":head,"pages":pages_ok,"total":total,"top_tokens":dec(tok),"top_senders":dec(send),"top_receivers":dec(recv),"top_pairs":pairs.most_common(20)}
json.dump(out, open("scratch/bsc-census3-48d09.json","w"))
print("head",head,"total",total,"pages",pages_ok)
print("senders:")
for a,c in out["top_senders"][:20]: print(a,c)
print("receivers:")
for a,c in out["top_receivers"][:15]: print(a,c)
