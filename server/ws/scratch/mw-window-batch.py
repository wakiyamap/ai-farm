import json, urllib.request, os, subprocess
URL=os.environ['RPC_RELAY_URL']; LANE='research'
CMP="0xfbb21d0380bee3312b33c4353c8936a0f13ef26c"; SEL="0x5ec88c79"
def call(to,data,block):
    p={"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},hex(block)]}
    rq=urllib.request.Request(f"{URL}/base?lane={LANE}",data=json.dumps(p).encode(),headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(rq,timeout=90).read())
    if 'error' in r: print("ERR",r['error'],block); return None
    return r['result']
def cls(w):
    v=int(w,16); return 'LIQ' if (v>>254) else 'OK'
rows=subprocess.run(['ledger','query','--json',"SELECT block, json_extract(fields,'$.borrower') AS holder, json_extract(fields,'$.repayAmount') AS repay FROM events WHERE source_id='moonwell_core.liquidate_borrow' AND (CAST(json_extract(fields,'$.repayAmount') AS INTEGER)>=10000000 OR CAST(json_extract(fields,'$.repayAmount') AS INTEGER) BETWEEN 4000000000000000 AND 1000000000000000000000) ORDER BY block"],capture_output=True,text=True).stdout
events=[json.loads(l) for l in rows.strip().splitlines()]
DEEP={'W6':(53268172,'0x733034d9bf322ad7eb1789d7c0de1eedd5892bf6'),'W7':(53265174,'0x78ce89c19f562f2090739015ec61da12ec26a460'),'W2':(53489444,'0x46795203f4ce3df6c054df9231168358e2e50fd3')}
out=[]
for ev in events:
    c=int(ev['block']); h=ev['holder']
    # step 1: d=8
    w=call(CMP, SEL+h[2:].rjust(64,'0'), c-8)
    if w is None: continue
    st=cls(w)
    rec={'block':c,'holder':h,'repay':ev['repay'],'liq8': st=='LIQ'}
    if st=='LIQ':
        # deep bracket for the three named events; else stop at LIQ(8)
        steps=[16384,32768] if any(DEEP[k][0]==c for k in DEEP) else [32]
        last=c-8
        for d in steps:
            w2=call(CMP, SEL+h[2:].rjust(64,'0'), c-d)
            if w2 is None: break
            if cls(w2)=='LIQ': last=c-d
            else: rec['crossing_block']=c-d; break
        rec['liq_back_to']=last
        rec['window_blocks_min']=c-last
    else:
        w3=call(CMP, SEL+h[2:].rjust(64,'0'), c-2)
        rec['liq2']= cls(w3)=='LIQ' if w3 else None
    out.append(rec)
    print(json.dumps(rec))
json.dump(out, open('scratch/mw-window-batch.json','w'), indent=1)
n8=sum(1 for r in out if r['liq8']); print(f"events={len(out)} window>=8blocks: {n8}")
