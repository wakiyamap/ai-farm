import json, os, time, urllib.request, collections, urllib.error

URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                d = json.loads(r.read())
            if "error" in d:
                print(method, "ERROR", json.dumps(d["error"])[:120], flush=True); time.sleep(1); continue
            return d["result"]
        except Exception as e:
            print(method, "EXC", e, flush=True); time.sleep(2)
    return None

USDC="0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
T0="0x"+"ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
head=int(rpc("eth_blockNumber"),16)
PAGES=20; PAGE=250
by_addr=collections.Counter(); per_page=[]
total_logs=0
for i in range(PAGES):
    a=head-PAGE*(i+1); b=a+PAGE-1
    logs=rpc("eth_getLogs",[{"topics":[T0],"fromBlock":hex(a),"toBlock":hex(b)}])
    if logs is None:
        per_page.append((a,"ERR")); continue
    per_page.append((a,len(logs)))
    total_logs+=len(logs)
    for L in logs:
        by_addr[L["address"]]+=1
    time.sleep(0.3)
out={"head":head,"page_blocks":PAGE,"pages":per_page,"total_logs":total_logs,
     "top_emitters":by_addr.most_common(30)}
json.dump(out, open("scratch/bsc-census-48d09-step3.json","w"))
print("head",head,"total",total_logs)
print("per page:", [p[1] for p in per_page])
print("top:")
for a,c in by_addr.most_common(20): print(a,c)
