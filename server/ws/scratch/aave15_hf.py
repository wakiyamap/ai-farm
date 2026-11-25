import json, subprocess
POOL='0x794a61358d6845594f94dc1db02a252b5b4814ad'; SEL='0xbf92857c'; RAY=10**18
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
    if not r or len(r) < 2+64*6: return None
    return int(r[2+64*5:2+64*6],16)
samp=json.load(open('scratch/aave15_sample.json'))
win=json.load(open('scratch/aave15_window.json'))
byblk={w['block']:w for w in win}
for r in samp:
    N=r['block']; user=r['u']
    d=0; hfN1=None; hfs={}
    for k in range(0,11):           # blocks N-1 .. N-11
        h=hf_at(user, N-1-k)
        if h is None: break
        hfs[N-1-k]=h/RAY
        if hfN1 is None: hfN1=h/RAY
        if h>=RAY: break
        d+=1
    w=byblk[N]
    w['window_blocks']=d; w['hf_prev']=hfN1; w['hf_trace']=hfs
    print(f"blk={N} win={d} hf(N-1)={hfN1 if hfN1 is None else round(hfN1,6)} trace={ {b:round(v,5) for b,v in hfs.items()} }", flush=True)
json.dump(win,open('scratch/aave15_window.json','w'))
print("done")
