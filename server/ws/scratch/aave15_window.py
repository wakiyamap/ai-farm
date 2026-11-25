import json, subprocess
POOL='0x794a61358d6845594f94dc1db02a252b5b4814ad'
SEL='0xbf92857c'
RAY=10**27
def rpc(method, params):
    for _ in range(3):
        p=subprocess.run(['python3','tools/rpc.py','arbitrum',method,json.dumps(params),'--lane','research'],
                         capture_output=True,text=True)
        try:
            j=json.loads(p.stdout)
            if 'result' in j and j['result'] is not None: return j['result']
        except Exception: pass
    return None
def hf_at(user, block):
    data=SEL+user[2:].rjust(64,'0')
    r=rpc('eth_call',[{'to':POOL,'data':data},'0x%x'%block])
    if not r or len(r)<68*6: return None
    words=[r[2+64*i:2+64*(i+1)] for i in range(6)]
    return int(words[5],16)   # healthFactor (last word), RAY
def hx(s): return int(s,16) if isinstance(s,str) else s
samp=json.load(open('scratch/aave15_sample.json'))
out=[]
for r in samp:
    N=r['block']; user=r['u']
    rec=rpc('eth_getTransactionReceipt',[r['tx_hash']])
    blk=rpc('eth_getBlockByNumber',['0x%x'%N, False])
    res={'block':N,'taker':r['liq'],'gross':round(r['gross'],2),'bonus_pct':round(r['bonus_pct'],2),
         'csym':r['csym'],'dsym':r['dsym'],'tx':r['tx_hash']}
    if rec:
        egp=hx(rec['effectiveGasPrice']); gasu=hx(rec['gasUsed'])
        res['gas_used']=gasu; res['egp_gwei']=egp/1e9
    if blk and blk.get('baseFeePerGas') is not None:
        bf=hx(blk['baseFeePerGas'])
        res['basefee_gwei']=bf/1e9
        if rec: res['priority_gwei']=(egp-bf)/1e9
    # walk back to find first block (going back) where HF>=1 -> takeable is the block after it
    d=0; hfb=None
    while d<10:
        h=hf_at(user, N-1-d)
        if h is None: break
        if h>=RAY: break   # not takeable at N-1-d; takeable = N-d
        d+=1; hfb=h
    res['window_blocks']=d            # consecutive pre-N blocks with HF<1
    res['hf_prev']= (hfb/RAY) if hfb is not None else None
    out.append(res)
    print(f"blk={N} win={d} pri={res.get('priority_gwei',-1):.3f}g egp={res.get('egp_gwei',-1):.3f}g gas={res.get('gas_used',-1)} hf(N-1)={res.get('hf_prev')} gross=${r['gross']:.2f}", flush=True)
json.dump(out,open('scratch/aave15_window.json','w'))
print("done", len(out))
