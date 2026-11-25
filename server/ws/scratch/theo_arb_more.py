import subprocess, json

def rpc(method, params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","arbitrum",method,json.dumps(params)],
                       capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        return ("ERR", (r.stdout + r.stderr).strip()[:300])
    try: return ("OK", json.loads(r.stdout).get("result"))
    except Exception: return ("ERR", r.stdout[:300])

# full topics for one of the 7d logs
st, logs = rpc("eth_getLogs", [{"address":"0x3ca8F12D7B376E9Ef338d1C432CA1b51DD319009",
  "fromBlock":hex(525804729),"toBlock":hex(525804729)}])
for l in logs: print("topics:", l["topics"], "data:", l["data"])
# from addresses of the 3 txs
for tx in ["0x9e3e88fd038fd2e8e83f981af93a029cce712cf8352abbb85a0648c747b3cfd5",
           "0x65e8323b6ee565fdc99b544d0489dc05acf3783b5c844661c225fe5c65ba34ca",
           "0x664b52fdab0f435f38a7134d0bbceaed178c6e1eec412a4ed0f37eadeb4091d1"]:
    st, t = rpc("eth_getTransactionByHash", [tx])
    if st=="OK": print(tx[:12], "from:", t["from"], "to:", t["to"])
    else: print(tx[:12], st)
# rollToNextRound from fresh address
sel = subprocess.run(["cast","sig","rollToNextRound(uint256)"],capture_output=True,text=True).stdout.strip()
print("rollToNextRound sel:", sel)
st, res = rpc("eth_call", [{"from":"0x7777777777777777777777777777777777777777",
  "to":"0x4fE17dEFc597cC3bD6fBe16135d8Ac42D421907e","data":sel+"0"*64}, "latest"])
print("rollToNextRound fresh addr:", st, res if st=="OK" else res[:200])
# token symbols
for tok in ["0x82af49447d8a07e3bd95bd0d56f35241523fbab1","0xaf88d065e77c8cC2239327C5EDb3A432268e5831","0x35751007A407CA6FEFFe80B3Cb397736d2cF4dbE"]:
    st, res = rpc("eth_call", [{"to":tok,"data":"0x95d89b41"},"latest"])
    sym = bytes.fromhex((res or "0x")[2:]).decode(errors="replace") if st=="OK" else "?"
    print(tok, "symbol:", sym)
