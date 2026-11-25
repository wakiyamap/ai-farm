import json, subprocess, datetime
va = ["0xf7D66b41Cd4241eae450fd9D2d6995754634D9f3","0xd0d2Ac44Cc842079e978bB11b094764f7D0dec6A","0x5B977577Eb8a480f63e11FC615D6753adB8652Ae","0xaD17A225074191d5c8a37B50FdA1AE278a2EE6A2","0x7D2382b1f8Af621229d33464340541Db362B4907"]
for a in va:
    out = subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","optimism","eth_call",
        json.dumps([{"to":a,"data":"0xc3535b52"},"latest"])],capture_output=True,text=True)
    r = json.loads(out.stdout)["result"]
    ts = int(r,16)
    print(a, datetime.datetime.utcfromtimestamp(ts).isoformat() if ts>0 else ts)
