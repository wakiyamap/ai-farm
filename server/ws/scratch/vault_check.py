import subprocess, json
RPC=['python3','/srv/farm/ws/tools/rpc.py','ethereum']
def call(to,data):
    r=subprocess.run(RPC+['eth_call',json.dumps([{'to':to,'data':data},'latest'])],capture_output=True,text=True)
    if r.returncode!=0: return 'ERR:'+r.stderr.strip()[:80]
    return json.loads(r.stdout)['result']
def sig(s):
    r=subprocess.run(['cast','sig',s],capture_output=True,text=True)
    return r.stdout.strip()
vaults=["0x0a2b94f6871c1d7a32fe58e1ab5e6dea2f114e56","0x6dc3ce9c57b20131347fdc9089d740daf6eb34c5","0xe800e3760fc20aa98c5df6a9816147f190455af3","0x35911af1b570e26f668905595ded133d01cd3e5a","0xa7569a44f348d3d70d8ad5889e50f78e33d80d35","0x79eb84b5e30ef2481c8f00fd0aa7aad6ac0aa54d","0x408b6a3e2daf288864968454aae786a2a042df36","0x52f0d57fb5d4780a37164f918746f9bd51c684a3","0xc7d7f434c015f2a7e77df9763ade300f2171a05a","0x1abd0403591be494771115d74ed9e120530f356e","0x2916dfb3324377645cac4c5e78dffce910a61393","0xd6246604313bd2884d205285aeefae07068fc58e"]
a_asset=sig('asset()'); a_total=sig('totalAssets()'); a_name=sig('name()')
for v in vaults:
    code=subprocess.run(RPC+['eth_getCode',json.dumps([v,'latest'])],capture_output=True,text=True)
    try: chash=json.loads(code.stdout)['result']
    except: chash='ERR'
    has=len(chash)>10
    res=call(v,a_asset)
    asset=res[-40:] if len(res)>=40 else res
    tot=call(v,a_total)
    totv=int(tot,16) if tot.startswith('0x') and len(tot)>2 else -1
    nm=call(v,a_name)
    name=''
    if nm.startswith('0x') and len(nm)>130:
        try:
            h=nm[2:]; l=int(h[64:128],16); name=bytes.fromhex(h[128:128+l*2]).decode()
        except: name=nm[:20]
    print(f"{v} code={'yes' if has else 'NO'} len={(len(chash)-2)//2} asset=0x{asset} totalAssets={totv} name={name}")
