import json, os, time, urllib.request, collections

URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            if "error" in d:
                print(method, "ERROR", json.dumps(d["error"])[:160]); time.sleep(2); continue
            return d["result"]
        except Exception as e:
            print(method, "EXC", e); time.sleep(3)
    return None

USDC="0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
T0="0x"+"ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
head=int(rpc("eth_blockNumber"),16)
out={"head":head,"pages":[]}

# decimals check on USDC
dec=rpc("eth_call",[{"to":USDC,"data":"0x313ce567"},"latest"])
out["usdc_decimals_raw"]=dec

PAGES=20; PAGE=1000
by_addr=collections.Counter(); by_token=collections.Counter(); per_block=[]
addr_tokens=collections.defaultdict(collections.Counter)
for i in range(PAGES):
    a=head-PAGE*(i+1); b=a+PAGE-1
    logs=rpc("eth_getLogs",[{"topics":[T0],"fromBlock":hex(a),"toBlock":hex(b)}])
    if logs is None:
        print("page failed", a); continue
    per_block.append((a,len(logs)))
    for L in logs:
        by_addr[L["address"]]+=1
        if L["address"]==USDC: addr_tokens["USDC"][L["address"]]
    out["pages"].append((a,len(logs) if logs is not None else None))
# topic0 per emitting token contract: to attribute logs to tokens we take addr only.
out["per_block_logs"]=per_block
out["top_emitters"]=by_addr.most_common(25)
json.dump(out, open("scratch/bsc-census-48d09-step2.json","w"))
print("decimals:", dec)
print("per-block logs:", [x[1] for x in per_block][:20])
print("top:", out["top_emitters"][:12])
