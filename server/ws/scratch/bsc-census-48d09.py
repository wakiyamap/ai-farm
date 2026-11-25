import json, os, time, urllib.request

URL = os.environ["RPC_RELAY_URL"] + "/bsc?lane=research"
def rpc(method, params=None):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type":"application/json"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            if "error" in d:
                print(method, "ERROR", json.dumps(d["error"])[:200]); time.sleep(2); continue
            return d["result"]
        except Exception as e:
            print(method, "EXC", e); time.sleep(3)
    return None

USDC="0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d"
CAKE="0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
TRANSFER=bytes.fromhex("ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef")

out={}
head=rpc("eth_blockNumber")
head=int(head,16); out["head"]=head
# block time: timestamps at head and head-3000
b1=rpc("eth_getBlockByNumber",[hex(head),False]); b2=rpc("eth_getBlockByNumber",[hex(head-3000),False])
t1=int(b1["timestamp"],16); t2=int(b2["timestamp"],16)
out["secs_per_block"]=(t1-t2)/3000
# USDC decimals check
dec=rpc("eth_call",[{"to":USDC,"data":"0x"+"ba575762"},"latest"])
out["usdc_decimals"]=dec
# USDC Transfer density over 3 x 1000 blocks
dens=[]
for i in range(3):
    a=head-1000*(i+1); logs=rpc("eth_getLogs",[{"address":USDC,"topics":[TRANSFER.hex()],"fromBlock":hex(a),"toBlock":hex(a+999)}])
    dens.append(len(logs) if logs is not None else "ERR")
out["usdc_transfer_per_1000_blocks"]=dens
json.dump(out, open("scratch/bsc-census-48d09-step1.json","w"), indent=1)
print(json.dumps(out))
