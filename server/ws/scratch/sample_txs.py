import subprocess, json, collections
addrs=["0x78a12b19e6aa81b8a8dbb15de160bf5cf4c24c6f","0xa9febd95da4bdd8946242721e4723325360ba4ae","0x7888cdcf82f483176ec0a18b972d52056f8d0b8a","0x139199c2299db69365107fa5e85f79544cabfc4c","0xa90db6bdedc8440309482719b906dd6d534103d1","0x2afcd10cee247e5cdb50f1d8b0f7dfe3b45586bc","0x127a7fe0cf3c0ab40f09b49fd872f05ab9e12d8e","0x92ec14dfc4b1a81a12af0dc7d0e9a04df96650ab","0xc6a3f3278c94d04d650b2f0df985994236d404ff","0x49ea44f34d2218f40371b2f093b8523f78a93652","0xccfb8e5e42b5c86531d51fcfd4c41b663d53fa81","0x122851569865faf5ac6a388f6a868f4c78c5348c","0x307b99ddae73137343addc6d5bcfd472e89d6f88"]
p=json.dumps([{"address":addrs,"fromBlock":hex(50876751),"toBlock":"latest"}])
o=subprocess.run(["python3","tools/rpc.py","hyperevm","eth_getLogs",p,"--lane","research"],capture_output=True,text=True)
logs=json.loads(o.stdout)["result"]
seen=[]
for l in logs:
    if l["transactionHash"] not in [s[0] for s in seen]:
        seen.append((l["transactionHash"],l["address"],l["topics"][0][:10]))
print("txs",len(seen))
senders=collections.Counter(); gasinfo=[]
for h,emitter,t0 in seen[:20]:
    o=subprocess.run(["python3","tools/rpc.py","hyperevm","eth_getTransactionByHash",json.dumps([h]),"--lane","research"],capture_output=True,text=True)
    t=json.loads(o.stdout)["result"]
    if t is None: continue
    senders[t["from"]]+=1
    gasinfo.append((h[:12],t["from"],t["to"],int(t.get("gasPrice","0x0"),16) if t.get("gasPrice") else 0))
for s,c in senders.most_common(): print("sender",s,c)
for g in gasinfo[:20]: print(g)
