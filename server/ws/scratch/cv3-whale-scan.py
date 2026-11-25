import json, subprocess, os, time
url=os.environ['RPC_RELAY_URL']
AB="0x9850ab1af75177e4a9201c65a2cf7976d5d28e40ef63494b44366f86b2f9412e"
BC="0xf891b2a411b0e66a5f0a6ff1368670fefa287a13f541eb633a386a1a9cc7046b"
ADDR=["0xb125e6687d4313864e53df431d5425969c15eb2f","0x9c4ec768c28520b50860ea7a15bd7213a9ff58bf","0x46e6b214b524310239732d51387075e0e70970bf"]
def call(params, method="eth_getLogs", tries=3):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    for t in range(tries):
        out=subprocess.run(['curl','-s','-X','POST',f'{url}/base?lane=research','-H','content-type: application/json','-d',body],capture_output=True,text=True,timeout=120).stdout
        try:
            j=json.loads(out)
        except Exception:
            time.sleep(2); continue
        if 'result' in j: return j['result']
        print("ERR",j.get('error'),params[0]['fromBlock']); time.sleep(3)
    raise SystemExit("relay fail")
HEAD=int(call([], "eth_blockNumber"),16)
SP=50000
lo=HEAD-90*43200  # ~90 days at 2s blocks
events=[]
reqs=0
for a in range(lo, HEAD, SP):
    b=min(a+SP-1,HEAD)
    res=call([{"fromBlock":hex(a),"toBlock":hex(b),"address":ADDR,"topics":[[AB,BC]]}])
    reqs+=1
    for lg in res:
        d=lg['data'][2:]
        vals=[int(d[i:i+64],16) for i in range(0,len(d),64)]
        ev={"block":int(lg['blockNumber'],16),"topic0":lg['topics'][0][:10],"tx":lg['transactionHash'],
            "addr":lg["address"],"topics":[t[:42] for t in lg["topics"][1:]],"vals":vals,"addr":lg["address"]}
        events.append(ev)
print("head",HEAD,"lo",lo,"reqs",reqs,"events",len(events))
absorb=[e for e in events if e['topic0']==AB[:10]]
buy=[e for e in events if e['topic0']==BC[:10]]
def bucket(vals,idx,th):
    return sum(1 for e in vals if len(e['vals'])>idx and e['vals'][idx]>=th)
absorb100=[e for e in absorb if len(e['vals'])>1 and e['vals'][1]>=100*10**8]
absorb1=[e for e in absorb if len(e['vals'])>1 and 10**8<=e['vals'][1]<100*10**8]
buy100=[e for e in buy if len(e['vals'])>0 and e['vals'][0]>=100*10**6]
days=(HEAD-lo)/43200
print(f"window_days={days:.1f} absorbs_total={len(absorb)} absorbs>=100USD={len(absorb100)} absorbs_1to100USD={len(absorb1)} absorbs<1USD={len(absorb)-len(absorb100)-len(absorb1)} buys_total={len(buy)} buys>=100USD={len(buy100)}")
for e in absorb100: print("WHALE-absorb", e['block'], e['tx'][:18], [e['vals'][0], e['vals'][1]])
for e in buy100: print("BUY>=100", e['block'], e['tx'][:18], e['topics'][0][:12], e['vals'][:2])
json.dump({"head":HEAD,"lo":lo,"days":days,"events":events}, open('/srv/farm/ws/scratch/cv3-whale/events.json','w'))
