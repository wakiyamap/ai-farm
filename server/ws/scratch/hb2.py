import json, subprocess, time
RPC=["python3","/srv/farm/ws/tools/rpc.py","hyperevm","eth_getLogs"]
CLAIM="0x2d43eb174787155132b52ddb6b346e2dca99302eac3df4466dbeff953d3c84d1"
FIN="0x8cc85b3d50ab2fb4e96570e702130699f959c4eb55d235f563f02ca5400d3c2a"
QUEUED="0xa2bc034e3400735d5038171f4a52ede4ca8a21acc010aab81996a18301cdf0a3"
INST="0x6edbbde848a1a11cab349ede80a2845202b7bdf4e6c4273d095ffd08ce15b569"
WM="0x9d0B0877b9f2204CF414Ca7862E4f03506822538"
windows=[(0x310c400,"control: window of known withdraw tx 51431201"),
         (0x308f808,"7d start"),(0x30b5a08,""),(0x30dbd08,""),(0x3102008,""),
         (0x3116c50,"window of updateExchangeRatio tx 51473488")]
name={CLAIM:"claim",FIN:"fin",QUEUED:"queued",INST:"instant"}
for a,note in windows:
    params=[{"fromBlock":hex(a),"toBlock":hex(a+999),"address":WM,"topics":[[CLAIM,FIN,QUEUED,INST]]}]
    r=subprocess.run(RPC+[json.dumps(params),"--lane","research"],capture_output=True,text=True)
    try: logs=json.loads(r.stdout)["result"]
    except Exception: print(a,note,"ERR",r.stdout[:90]); time.sleep(4); continue
    counts={}
    for l in logs:
        k=name.get(l["topics"][0].lower(),l["topics"][0][:10]); counts[k]=counts.get(k,0)+1
    print(hex(a),note,"->",counts if counts else "no events", [l["transactionHash"][:14] for l in logs][:3])
    time.sleep(2)
