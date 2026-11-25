import sys, json; sys.path.insert(0,'/srv/farm/ws/scratch')
exec(open('/srv/farm/ws/scratch/uv2opt.py').read())
pairs=json.load(open('/srv/farm/ws/scratch/uv2opt_pairs.json'))
FRESH='0x1111111111111111111111111111111111111111'
def dec(t):
    r=callfn(t,'decimals()')
    return None if isinstance(r,dict) else int(r,16)
def bal(t,who):
    r=call(t, sel('balanceOf(address)')+'00'*12+who[2:])
    return None if isinstance(r,dict) else int(r,16)
out={}
for name,p in pairs.items():
    if p is None: continue
    code=rpc('eth_getCode',[p,'latest'])
    t0=addr(callfn(p,'token0()')); t1=addr(callfn(p,'token1()'))
    res=callfn(p,'getReserves()')
    if isinstance(res,dict): print(name,'reserves err',res); continue
    r0=int(res[2:66],16); r1=int(res[66:130],16); ts=int(res[130:194],16)
    b0=bal(t0,p); b1=bal(t1,p)
    sk=call(p, sel('skim(address)')+'00'*12+FRESH[2:])  # eth_call from fresh addr
    # simulate skim: what would be transferred -> use balance-reserve
    out[name]=dict(pair=p, code_len=len(code)//2-1 if isinstance(code,str) else 0,
                   token0=t0, token1=t1, dec0=dec(t0), dec1=dec(t1),
                   res0=r0, res1=r1, bal0=b0, bal1=b1,
                   pot0=(b0-r0) if (b0 is not None) else None,
                   pot1=(b1-r1) if (b1 is not None) else None,
                   skim_call='ok' if not isinstance(sk,dict) else sk,
                   block_ts_last=ts)
    print(name, json.dumps(out[name]))
json.dump(out, open('/srv/farm/ws/scratch/uv2_opt_meas.json','w'), indent=1)
