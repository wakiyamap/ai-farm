import subprocess, json, sys
RPC=['python3','/srv/farm/ws/tools/rpc.py','ethereum']
def rpc(m,p,tries=1):
    for i in range(tries+1):
        r=subprocess.run(RPC+[m,json.dumps(p)],capture_output=True,text=True)
        try: d=json.loads(r.stdout)
        except: continue
        if 'result' in d: return ('ok', d['result'])
        if 'error' in d: return ('err', d['error'])
    return ('fail', r.stdout[:80]+r.stderr[:80])
vaults={"autoETH":"0x0a2b94f6871c1d7a32fe58e1ab5e6dea2f114e56","balETH":"0x6dc3ce9c57b20131347fdc9089d740daf6eb34c5","autoLRT":"0xe800e3760fc20aa98c5df6a9816147f190455af3","dineroETH":"0x35911af1b570e26f668905595ded133d01cd3e5a","autoUSD":"0xa7569a44f348d3d70d8ad5889e50f78e33d80d35","autoDOLA":"0x79eb84b5e30ef2481c8f00fd0aa7aad6ac0aa54d","siloUSD":"0x408b6a3e2daf288864968454aae786a2a042df36","siloETH":"0x52f0d57fb5d4780a37164f918746f9bd51c684a3","infinifiUSD":"0xc7d7f434c015f2a7e77df9763ade300f2171a05a","anchrgUSD":"0x1abd0403591be494771115d74ed9e120530f356e","gpuUSD":"0x2916dfb3324377645cac4c5e78dffce910a61393","morphoTenUSDC":"0xd6246604313bd2884d205285aeefae07068fc58e"}
FRESH='0x8888888888888888888888888888888888888888'
ud='0x544407e2'+(1).to_bytes(32,'big').hex()
w='00'*64
enc='0xdc47c23a'+w+(0x60).to_bytes(32,'big').hex()+(0x120).to_bytes(32,'big').hex()+'00'*192+(0).to_bytes(32,'big').hex()+(0).to_bytes(32,'big').hex()
print("== updateDebtReporting(1) from 0x8888.. ==")
for n,v in vaults.items():
    k,r=rpc('eth_call',[{'from':FRESH,'to':v,'data':ud},'latest'])
    print(n, 'OK' if k=='ok' else (k, (r.get('data') or r.get('message',''))[:20] if k=='err' else r))
print("== flashRebalance(dummy) from 0x8888.. ==")
for n in ["autoETH","autoUSD","autoDOLA","siloUSD","siloETH"]:
    k,r=rpc('eth_call',[{'from':FRESH,'to':vaults[n],'data':enc},'latest'])
    print(n, 'OK' if k=='ok' else (k, (r.get('data') or r.get('message',''))[:20] if k=='err' else r))
