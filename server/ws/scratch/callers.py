import subprocess, json, collections
logs=json.load(open('scratch/logs7d.json'))
RPC=['python3','/srv/farm/ws/tools/rpc.py','ethereum']
def rpc(m,p):
    r=subprocess.run(RPC+[m,json.dumps(p)],capture_output=True,text=True)
    d=json.loads(r.stdout); return d.get('result')
DDR='0x1db39a4dd19a509f787f01f9e81390b259e2b4f34d4a7fb9a76d344e3078c5d6'
RS='0xeb13b2b1ecae8f425568fdea9b34f9a48f28df89c027ee34637cb798234b6153'
ddr_txs=sorted({l['transactionHash'] for l in logs if l['topics'][0]==DDR})
rs_txs=sorted({l['transactionHash'] for l in logs if l['topics'][0]==RS})
print("DDR txs:",len(ddr_txs),"RS txs:",len(rs_txs))
def sample(txs,n=4):
    step=max(1,len(txs)//n); out=txs[::step][:n]
    return out
froms=collections.Counter()
gas_info=[]
for kind,txs in (('DDR',ddr_txs),('RS',rs_txs)):
    for h in sample(txs):
        rc=rpc('eth_getTransactionReceipt',[h])
        if rc is None: print(kind,h,'receipt null'); continue
        froms[(kind,rc['from'].lower())]+=1
        gas_info.append((kind,h,rc['from'],int(rc['gasUsed'],16),int(rc['effectiveGasPrice'],16)))
print("sample receipts:")
for g in gas_info: print(g[0],g[1][:16],g[2],'gas',g[3],'gwei %.2f'%(g[4]/1e9))
# callers from logs: need tx.from per tx — too many receipts; instead who emits = sample only. Print unique froms in sample
print(froms)
# Transfers to callers: gather all caller addresses from ALL txs? sample-based. Check transfers in log set whose 'to' matches any sample caller
callers={g[2].lower() for g in gas_info}
tr=[l for l in logs if l['topics'][0].startswith('0xddf252ad')]
to_hits=[l for l in tr if len(l['topics'])>2 and ('0x'+l['topics'][2][-40:].lower()) in callers]
print("transfer logs to sampled callers:",len(to_hits))
json.dump({'ddr':ddr_txs,'rs':rs_txs,'gas':gas_info},open('scratch/callers.json','w'))
