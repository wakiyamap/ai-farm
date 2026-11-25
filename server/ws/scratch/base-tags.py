import json, urllib.request, os, time, sys
sys.path.insert(0,"/srv/farm/ws/scratch")
from checksum import to_checksum
url=os.environ["RPC_RELAY_URL"]+"/base?lane=research"
def rpc(m,p):
    b=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    for attempt in range(10):
        try:
            r=json.loads(urllib.request.urlopen(urllib.request.Request(url,b,{"content-type":"application/json"}),timeout=90).read())
            if "result" in r: return r["result"]
            print("err",r["error"].get("code"),str(r["error"].get("message"))[:80]); time.sleep(2)
        except Exception as e:
            print("ex",e); time.sleep(2)
    raise RuntimeError("rpc failed")
head=rpc("eth_blockNumber",[])
head=int(head,16)
T_START="0xf18b757d93c36d059284838a0328b06d8eb30d7214ffadde3266465a0006f6b3"
T_SETT="0x058fb1fa484531f400806f666315faf1a45941db93ba069405882b78ba40dc87"
tags={"bsdETH":["0x07f58c529170645f3df1c277bedc176eceb97a0e","0x8c46348552bdab72dd163928fd8460257089f8f9"],
"hyUSD":["0xef34c651f1ae9593cfb2cd02da800a4aad612bd","0xcc03e97f6e2e4efb50ab95c89bb4b27911105736"]}
res={}
for tag,addrs in tags.items():
    for name,t0 in (("started",T_START),("settled",T_SETT)):
        evs=[]
        for a in addrs:
            frm=head-1300000
            while frm<=head:
                to=min(frm+40000-1,head)
                evs.extend(rpc("eth_getLogs",[{"fromBlock":hex(frm),"toBlock":hex(to),"address":[to_checksum(a)],"topics":[t0]}]))
                frm=to+1
        res.setdefault(tag,{})[name]=evs
        print(tag,name,len(evs),"head",head,flush=True)
json.dump({t:{k:[{"block":int(l["blockNumber"],16),"trade":l["topics"][1][-40:],"sell":l["topics"][2][-40:],"buy":l["topics"][3][-40:],"data":l["data"][2:],"tx":l["transactionHash"]} for l in v] for k,v in d.items()} for t,d in res.items()}, open("scratch/base-tags.json","w"))
