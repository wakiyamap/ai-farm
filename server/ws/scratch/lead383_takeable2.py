import subprocess, json, math
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
MP={'0x9103c3b4':('0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836','0x663becd10dae6c4a3dcd89f1d76c1174199639b9',0x0bef55718ad60000),
'0x8793cf30':('0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda','0xfea2d58cefcb9fcb597723c6bae66ffe4193afe4',None),
'0xd4a903dc':('0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109','0x031b2efc8d70042ac8d9f5c793c4149ec4b60fde',None)}
def rpc(to,data,blk):
    blk = blk if isinstance(blk,str) else hex(blk)
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','base','eth_call',json.dumps([{'to':to,'data':data},blk])],capture_output=True,text=True)
    try: return json.loads(p.stdout)['result']
    except Exception: return None
lltv_cache={}
def lltv_of(mid):
    if mid not in lltv_cache:
        r=rpc(MORPHO,'0x2c3c9157'+mid[2:],'latest')
        lltv_cache[mid]=int(r[2:][4*64:5*64],16)
    return lltv_cache[mid]
def liq_at(mid, oracle, b, blk):
    pos=rpc(MORPHO,'0x93c52062'+mid[2:]+b[2:].rjust(64,'0'),blk)
    if pos is None: return None
    mkt=rpc(MORPHO,'0x5c60e39a'+mid[2:],blk)
    pr=rpc(oracle,'0xa035b1fe',blk)
    if not mkt or not pr: return None
    pw=[pos[2:][i*64:(i+1)*64] for i in range(3)]
    mw=[mkt[2:][i*64:(i+1)*64] for i in range(6)]
    bs=int(pw[1],16); col=int(pw[2],16)
    tba=int(mw[2],16); tbs=int(mw[3],16)
    price=int(pr,16); ll=lltv_of(mid)
    ba=math.ceil(bs*tba/tbs) if tbs else 0
    mb=col*price//10**36*ll//10**18
    return ba>mb
out=json.load(open('/srv/farm/ws/scratch/lead383_probe_out.json'))
res=[]
for s in out[:5]:
    mid,oracle,_=MP[s['mkt']]
    C=s['block']; b=s['borrower']
    row={'block':C,'tx':s['tx'],'borrower':b[:10],'gross':s['gross']}
    left=C-1500
    v=liq_at(mid,oracle,b,C-1)
    row['liq_Cminus1']=v
    vl=liq_at(mid,oracle,b,left)
    if v is None: row['blocks']='rpc-fail'; res.append(row); print(json.dumps(row),flush=True); continue
    if not v: row['blocks']=0; res.append(row); print(json.dumps(row),flush=True); continue
    if vl: row['blocks']='>=1499'; res.append(row); print(json.dumps(row),flush=True); continue
    lo,hi=left,C-1
    while lo+1<hi:
        m=(lo+hi)//2
        if liq_at(mid,oracle,b,m): hi=m
        else: lo=m
    row['blocks']=C-1-hi; row['first_takeable_block']=hi
    res.append(row); print(json.dumps(row),flush=True)
json.dump(res,open('/srv/farm/ws/scratch/lead383_takeable2.json','w'),indent=1)
