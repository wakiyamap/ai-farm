import json, subprocess
FB, TB = "0x19302bf", "0x193c72b"
T0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
def logs(params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_getLogs",json.dumps(params)],
                       capture_output=True, text=True)
    try: return json.loads(r.stdout)["result"]
    except Exception: return {"ERR": r.stdout[:200]+r.stderr[:200]}
ad71 = "0x" + "ad713bd85e8bff9ce85ca03a8a930e4a38f6893d".rjust(64,"0")
cbbtc = "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf"
# control: any WBTC Transfer in a recent 5000-block window (no address filter on topic shape, topics=[T0] only is huge; use address=WBTC)
ctrl = logs([{"fromBlock":"0x193c5ff","toBlock":TB,"address":"0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599","topics":[T0]}])
print("WBTC control last ~5k blocks:", len(ctrl) if isinstance(ctrl,list) else ctrl)
ctrl2 = logs([{"fromBlock":"0x193c5ff","toBlock":TB,"address":"0xC96dE26018A54D51c097160568752c4E3BD6C364","topics":[T0]}])
print("LBTC control last ~5k blocks:", len(ctrl2) if isinstance(ctrl2,list) else ctrl2)
din = logs([{"fromBlock":FB,"toBlock":TB,"address":cbbtc,"topics":[T0,None,ad71]}])
print("cbBTC in count:", len(din))
senders = {}
total = 0
for lg in din:
    f = "0x"+lg["topics"][1][-40:]
    v = int(lg["data"],16)
    senders[f] = senders.get(f,0)+1
    total += v
print("cbBTC in total (raw):", total, "= BTC units", total/1e8)
print("senders:", senders)
dout = logs([{"fromBlock":FB,"toBlock":TB,"address":cbbtc,"topics":[T0,ad71]}])
for lg in dout:
    t = "0x"+lg["topics"][2][-40:]
    print("OUT tx", lg["transactionHash"], "block", int(lg["blockNumber"],16), "to", t, "value", int(lg["data"],16)/1e8)
