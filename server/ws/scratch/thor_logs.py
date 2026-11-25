import subprocess, json, collections
RPC="/srv/farm/ws/tools/rpc.py"
latest=0x38f6c3a
span=3_024_000
from_b=latest-span
CH=450_000
topics={"dep0":"ef519b7eb82aaf6ac376a6df2d793843ebfd593de5f1a0601d3cc6ab49ebb395",
 "tro":"a9cd03aa3c1b4515114539cd53d22085129d495cb9e9f9af77864526240f1bf7",
 "toc":"8e5841bcd195b858d53b38bcf91b38d47f3bc800469b6812d35451ab619c6f6c",
 "tfail":"a6a370fa655359af5f69091e908830c250b8daffb80f6b578741423ae4c47ab1",
 "tocv2":"de470d7c2e9c3282cad476e5ed6f05f74d68839c406573048f2dee22a8c452c7",
 "tall":"05b90458f953d3fcb2d7fb25616a2fddeca749d0c47cc5c9832d0266b5346eea"}
rev={v:k for k,v in topics.items()}
addr="0x00dc6100103bc402d490aee3f9a5560cbd91f1d4"
cnt=collections.Counter(); samples=[]
b=from_b
while b<=latest:
    e=min(b+CH-1,latest)
    p=json.dumps([{"address":addr,"fromBlock":hex(b),"toBlock":hex(e)}])
    r=subprocess.run(["python3",RPC,"base","eth_getLogs",p],capture_output=True,text=True)
    if r.returncode!=0:
        print("ERR",hex(b),r.stderr[:150]); break
    try: logs=json.loads(r.stdout)["result"]
    except Exception as ex: print("PARSE",hex(b),r.stdout[:100]); break
    for l in logs:
        t=l["topics"][0][2:]; cnt[rev.get(t,"other:"+t[:12])]+=1
    if logs: samples.append((hex(b),hex(e),len(logs)))
    b=e+1
print("7d counts:",dict(cnt),"total",sum(cnt.values()))
print("chunks with logs:",samples[:10])
