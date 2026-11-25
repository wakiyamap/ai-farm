import json, urllib.request, os
URL = os.environ["RPC_RELAY_URL"]; LANE="research"
def rpc(method, params):
    req = urllib.request.Request(f"{URL}/hyperevm?lane={LANE}",
        data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
        headers={"content-type":"application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=40).read())
    if "error" in r: print("ERR", method, r["error"]); return None
    return r["result"]
head = int(rpc("eth_blockNumber",[]),16)
cands = {
 "0x6d18f44e6b64e5e44bbaca1ca534a8290bd331b5": "0x2745cbaa0aafc99b5285e5ade53fdf79c2a488f5",
 "0xdf1bda875c9393a663ce69bf6a7fbaa73dfd053d": "0x6cd5661646289fb6e65ea5c032310fded797d0a2",
 "0x33b12dd75f66933acd6438594d80cf91cacdc10b": "0xf9b0c8ee13ae2fc0665764ecbdb417685dea8081",
 "0xaea0edc9ae3939f89e11d19d09d96a32ccefb5e2": "0xce59f8b65ad41c9dae4c07a0571a39824bd92cff",
}
import collections
for caller, target in cands.items():
    print(f"\n== {caller[:8]} -> {target[:8]}")
    logs = rpc("eth_getLogs",[{"address":[target],"fromBlock":hex(head-6000),"toBlock":hex(head-10)}])
    if logs is None: logs=[]
    txs = collections.Counter(); inputs=collections.Counter()
    print("logs:", len(logs))
    # pick a recent tx by caller
    sample=None
    for lg in logs[-1:]:
        h = lg["transactionHash"]
        t = rpc("eth_getTransactionByHash",[h])
        if t and t["from"].lower()==caller.lower():
            sample=t; break
    if not logs:
        print("no logs; need tx from block scan")
        continue
    if sample is None:
        # try earlier logs from the tail until caller matches
        for lg in reversed(logs):
            t = rpc("eth_getTransactionByHash",[lg["transactionHash"]])
            if t and t["from"].lower()==caller.lower(): sample=t; break
            inputs[t["input"][:10]]+=1
    if sample:
        sel=sample["input"][:10]; print("caller tx: selector",sel,"to",sample["to"][:10],"value",sample["value"])
        r = rpc("eth_getTransactionReceipt",[sample["hash"]])
        if r:
            gu=int(r["gasUsed"],16); gp=int(r.get("effectiveGasPrice","0x1"),16)
            print(f"gasUsed {gu} gasPrice {gp/1e9:.9f} HYPE cost/tx {gu*gp/1e18:.8f} HYPE")
    # payments to caller over ~7d
    tr = rpc("alchemy_getAssetTransfers",[{"fromBlock":hex(head-300000),"toBlock":hex(head-100),"category":["external"],"maxCount":"0x64","toAddress":caller}])
    if tr:
        tds=[t for t in tr["transfers"] if t.get("asset")==t.get("asset") ]
        native=[t for t in tr["transfers"] if t.get("asset")=="ETH" and t.get("from") not in (None,"")]
        tot=sum(float(t.get("rawValue") or 0) for t in native)
        frs=collections.Counter(t["from"] for t in native)
        print(f"7d inbound native to caller: {len(native)} transfers, {tot:.4f} HYPE, from: {dict(list(frs.most_common(5)))}")
