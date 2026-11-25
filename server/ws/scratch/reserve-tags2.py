import json, urllib.request, os, time
import sys; sys.path.insert(0,"/srv/farm/ws/scratch")
from checksum import to_checksum
url0 = os.environ["RPC_RELAY_URL"]
def rpc(chain, lane, m, p):
    u = f"{url0}/{chain}?lane={lane}"
    b = json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode()
    for attempt in range(8):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(u, b, {"content-type":"application/json"}), timeout=90).read())
            if "error" in r:
                print("err", r["error"].get("code"), str(r["error"].get("message"))[:90]); time.sleep(1.5*(attempt+1)); continue
            return r["result"]
        except Exception as e:
            print("ex", e); time.sleep(3)
    raise RuntimeError("rpc failed")

T_START = "0xf18b757d93c36d059284838a0328b06d8eb30d7214ffadde3266465a0006f6b3"
T_SETT  = "0x058fb1fa484531f400806f666315faf1a45941db93ba069405882b78ba40dc87"
watched_eth = ["0xe04c26f68e0657d402fa95377aa7a2838d6cba6f","0x3d5ebb5399243412c7e895a7aa468c7cd4b1014a","0x6e20823ca50aa026b99789c8d468a01f8aa3581c","0x977cb0e300a58978f597fc65ed5a2d2784d2dcf9"]
new_eth = {  # tag -> traders
 "hyUSD":["0x0771301d56eb734a5f61d275da1b6c2459a00dc7","0x4886f5549d3b25adcfac68e40062c735faf81378"],
 "USD3":["0x1ae6d94992e87056a92ba2e9eb54cf3ad3ef55d6","0x52d307a4ee4e42a799b3354ad54564a5b4cfc260"],
 "USDC+":["0x892e53828e264c142c929ce8f852352e6b799e19","0x0a1c10727f7ae292521078dfc1280c6c01277eef"],
}
new_base = {
 "bsdETH":["0x07f58c529170645f3df1c277bedc176eceb97a0e","0x8c46348552bdab72dd163928fd8460257089f8f9"],
 "hyUSD":["0xef34c651f1ae9593cfb2cd02da800a4aad612bd","0xcc03e97f6e2e4efb50ab95c89bb4b27911105736"],
}
def census(chain, days, addrs_by_tag, extra_addrs, page_blocks):
    head = int(rpc(chain,"research","eth_blockNumber",[]),16)
    frm0 = head - int(days*86400/ (12 if chain=="ethereum" else 2))
    res = {}
    for name, t0 in (("started",T_START),("settled",T_SETT)):
        frm = frm0
        logs=[]
        while frm <= head:
            to = min(frm+page_blocks-1, head)
            addrs = [to_checksum(a) for a in (extra_addrs+sum(addrs_by_tag.values(),[]))]
            if chain=="base":  # public fallback node rejects multi-address arrays
                for aa in addrs:
                    logs.extend(rpc(chain,"research","eth_getLogs",[{"fromBlock":hex(frm),"toBlock":hex(to),"address":[aa],"topics":[t0]}]))
            else:
                logs.extend(rpc(chain,"research","eth_getLogs",[{"fromBlock":hex(frm),"toBlock":hex(to),"address":addrs,"topics":[t0]}]))
            frm = to+1
        res[name]=logs
        print(chain,name,len(logs),"head",head)
    return res
def summarize(res, tags):
    import collections
    out=collections.defaultdict(dict)
    seen=collections.Counter()
    for k in ("started","settled"):
        for lg in res[k]:
            addr = lg["address"].lower()
            tag = None
            for t,addrs in tags.items():
                if addr in [a.lower() for a in addrs]: tag=t
            if tag is None: tag="WATCHED"
            d = out[tag].setdefault(k,[]); 
            d.append({"block":int(lg["blockNumber"],16),"trade":lg["topics"][1][-40:],"sell":lg["topics"][2][-40:],"buy":lg["topics"][3][-40:],"data":lg["data"][2:],"tx":lg["transactionHash"]})
    return out
eth_tags = {**new_eth}; base_tags={**new_base}
r_eth = census("ethereum", 30, eth_tags, watched_eth, 40000)
r_base= census("base", 30, base_tags, [], 40000)
se=summarize(r_eth, eth_tags); sb=summarize(r_base, base_tags)
json.dump({"eth":dict(se),"base":dict(sb)}, open("scratch/reserve-tags2.json","w"), default=str)
for chain,s in (("eth",se),("base",sb)):
    for tag,v in s.items():
        st=v.get("started",[]); se_=v.get("settled",[])
        print(chain,tag,"started",len(st),"settled",len(se_), "first", st[0]["block"] if st else None)
