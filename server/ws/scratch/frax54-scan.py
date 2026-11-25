import json,urllib.request,os,sys
url=os.environ["RPC_RELAY_URL"]+"/ethereum?lane=research"
T0="0x35f432a64bd3767447a456650432406c6cacb885819947a202216eeea6820ecf"
HEAD=26362539
def post(fb,tb):
    d={"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"topics":[T0],"fromBlock":hex(fb),"toBlock":hex(tb)}]}
    req=urllib.request.Request(url,data=json.dumps(d).encode(),headers={"content-type":"application/json"})
    return json.loads(urllib.request.urlopen(req,timeout=20).read())
W=10000
start=HEAD-126000
logs=[]
for fb in range(start,HEAD+1,W):
    tb=min(fb+W-1,HEAD)
    r=post(fb,tb)
    if "error" in r:
        print("ERR",r["error"]["message"][:80],hex(fb),file=sys.stderr)
        sys.exit(1)
    logs+=r["result"]
print("30d total logs:",len(logs))
ctrl=[l for l in logs if int(l["blockNumber"],16)==26337186]
print("positive control 26337186:",len(ctrl))
json.dump(logs,open("scratch/frax54-logs.json","w"))
