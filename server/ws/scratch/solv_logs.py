import json, subprocess
FB, TB = "0x19302bf", "0x193c72b"
T0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
toks = {"WBTC":"2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "LBTC":"C96dE26018A54D51c097160568752c4E3BD6C364",
        "cbBTC":"cbB7C0000aB88B473b1f5aFd9ef808440eed33Bf"}
addrs = ["51c2ba3c5e8a90e7c27fa9ec8b287454eb698ead",
         "be6297731720b7e218031ca8970921f9b41f3d00",
         "ad713bd85e8bff9ce85ca03a8a930e4a38f6893d",
         "9bc8ef6bb09e3d0f3f3a6cd02d2b9dc3115c7c5c"]
def logs(params):
    r = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","ethereum","eth_getLogs",json.dumps(params)],
                       capture_output=True, text=True)
    try: return json.loads(r.stdout)["result"]
    except Exception: return {"ERR": r.stdout[:150]+r.stderr[:150]}
for name,tok in toks.items():
    for a in addrs:
        p = "0x" + a.rjust(64, "0")
        din  = logs([{"fromBlock":FB,"toBlock":TB,"address":"0x"+tok,"topics":[T0,None,p]}])
        dout = logs([{"fromBlock":FB,"toBlock":TB,"address":"0x"+tok,"topics":[T0,p]}])
        ni = len(din) if isinstance(din,list) else din
        no = len(dout) if isinstance(dout,list) else dout
        print(f"{name} {a[:6]}.. in={ni} out={no}")
