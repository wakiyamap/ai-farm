import subprocess, json

def rpc(chain, method, params):
    r = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py',chain,method,json.dumps(params)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"rpc fail {method} {params}: {r.stdout[:200]} {r.stderr[:200]}")
    out = json.loads(r.stdout[r.stdout.index('{'):])
    return out['result']

pairs = {
 '0xd58878b45ed22b18fa2590da7f3f53885d7e6ab4':'DAI/FUN',
 '0x853ee4b2a13f8a742d64c8f088be7ba2131f670d':'USDC/WETH',
 '0x6e7a5fafcec6bb1e78bae2a1f0b612012bf14827':'WMATIC/USDC',
}
for p,name in pairs.items():
    t0 = rpc('polygon','eth_call',[{'to':p,'data':'0x0dfe1681'},'latest'])[26:]
    t1 = rpc('polygon','eth_call',[{'to':p,'data':'0xd21220a7'},'latest'])[26:]
    res = rpc('polygon','eth_call',[{'to':p,'data':'0x0902f1ac'},'latest'])[2:]
    r0, r1 = int(res[0:64],16), int(res[64:128],16)
    b0 = int(rpc('polygon','eth_call',[{'to':'0x'+t0,'data':'0x70a08231000000000000000000000000'+p[2:]},'latest'])[2:],16)
    b1 = int(rpc('polygon','eth_call',[{'to':'0x'+t1,'data':'0x70a08231000000000000000000000000'+p[2:]},'latest'])[2:],16)
    print(name, p, 'token0=0x'+t0, 'token1=0x'+t1)
    print('  pot0 =', b0-r0, ' pot1 =', b1-r1)
