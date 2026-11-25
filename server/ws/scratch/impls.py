import subprocess, json
RPC=['python3','/srv/farm/ws/tools/rpc.py','ethereum']
def rpc(m,p):
    r=subprocess.run(RPC+[m,json.dumps(p)],capture_output=True,text=True)
    if r.returncode!=0: return 'ERR:'+r.stderr.strip()[:100]
    return json.loads(r.stdout)['result']
SLOT_1967='0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
vaults={"autoETH":"0x0a2b94f6871c1d7a32fe58e1ab5e6dea2f114e56","balETH":"0x6dc3ce9c57b20131347fdc9089d740daf6eb34c5","autoLRT":"0xe800e3760fc20aa98c5df6a9816147f190455af3","dineroETH":"0x35911af1b570e26f668905595ded133d01cd3e5a","autoUSD":"0xa7569a44f348d3d70d8ad5889e50f78e33d80d35","autoDOLA":"0x79eb84b5e30ef2481c8f00fd0aa7aad6ac0aa54d","siloUSD":"0x408b6a3e2daf288864968454aae786a2a042df36","siloETH":"0x52f0d57fb5d4780a37164f918746f9bd51c684a3","infinifiUSD":"0xc7d7f434c015f2a7e77df9763ade300f2171a05a","anchrgUSD":"0x1abd0403591be494771115d74ed9e120530f356e","gpuUSD":"0x2916dfb3324377645cac4c5e78dffce910a61393","morphoTenUSDC":"0xd6246604313bd2884d205285aeefae07068fc58e"}
for n,v in vaults.items():
    code=rpc('eth_getCode',[v,'latest'])
    impl=None
    if code.startswith('0x3660306000600037') or code[:6] in ('0x366',):
        impl='0x'+code[22:64]  # EIP1167
    if code.startswith('0x3660306000600037600036600073'):
        impl='0x'+code[26:66]
    if impl is None or len(impl)!=42:
        s=rpc('eth_getStorageAt',[v,SLOT_1967,'latest'])
        impl='0x'+s[-40:]
    print(n,v,'impl',impl, 'codehead', code[:20])
