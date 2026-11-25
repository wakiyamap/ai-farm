import json, subprocess, datetime

CHAIN='hyperevm'
ACTOR='0xf76ead30ee64192e30ec26f7c39a4b069b9c1ccf'
EXEC='0x1b8e94763019968d1a3b8d586c5ef96d8ac3a9f6'
BENEFICIARY='0xa9dd620fc1b6316ce75c8059aaed1f5fa5e0cefb'
HASHES='''0xe8b482043b3d3ed01fb3914120fc81e635c458d0bc02fa09e81711203f69796e
0x4c001ab0b965abb2a853c2fcc6debfe9f5d63acc67e6f974a63aac15954c682b
0xddb3b20b55063f509e2414bc058b41a63efc5fc1b73e4853b201d31d81f46417
0x5b386cb13a6b6b492e271d52dc737ba9b411c27b77e9b01054c61762ca311c6b
0x7f626a03bc0c9cbd1ab8c3bf3579862a167057a16f0a739a1e02d1f324db8ef4
0x87b7afd0bfd7bda0895e99489cec139fcff1ccf3cdad8d8c5007991a4fad13ad
0xf2d0848a0be988f03dcc3dbc05245e65d699ad9952601dd91472bea92a0f3458
0x16d785f879a15fc8f65f8bb4e21ee923d75328c86107ea5395a44e47b248cf87
0xba320a1a1221aca2807faf3af8559f11bba5383fc905804b78546e00d3cb5253
0x4a02997e7ae784c84a9313b839c7e747f6af771fd3e7e1d520da6f14d787bd68
0x7791c7daf515407363bd8ad3ae8f06c5db15e4ef4fc902724068edd850e0eff1
0x88b9f40681f1f2b8ee4f6698977b2f1e6ff46d22a8865840f23801de140f51b6
0x55a08f5da50bd0a6a399f64f586fd527e266440b81376491a0186c33265fa0db
0xfd5431f03239ce841d3c0a37b753cb7b401e677b89b117fb6d4a727eb655c4a5
0x07a2a76cdc195db5b8e3ffb593d25ef033caa0d0f91fa2c4c1d60ab6e08d3845
0x71b427aad24c9670ae7a982e0a20d6c37243b9034e5c3aacf21c81666c989f9b
0x196352e27d888ef8bcb2a1526648e733748b57c87bc475b030ef52918d63865a
0x750d1aa470670592585175f383c6a9300e057dd8cff5c98a32eb8ceb7ad49354
0xae11bc1e5c3b4b843d0c81b4989bbf11ad29140d8a5e126cd6e8f050cf2d99c4'''.split()

def rpc(method,params):
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py',CHAIN,method,json.dumps(params)],capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr or p.stdout)
    o=json.loads(p.stdout)
    if 'error' in o: raise RuntimeError(o['error'])
    return o['result']

TRANSFER='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
def net(logs,who):
    out={}
    for log in logs:
        t=log['topics']
        if len(t)<3 or t[0].lower()!=TRANSFER: continue
        frm='0x'+t[1][-40:].lower(); to='0x'+t[2][-40:].lower()
        amount=int(log['data'],16)
        if frm==who: out[log['address'].lower()]=out.get(log['address'].lower(),0)-amount
        if to==who: out[log['address'].lower()]=out.get(log['address'].lower(),0)+amount
    return {k:v for k,v in out.items() if v}

if __name__=='__main__':
    for h in HASHES:
        r=rpc('eth_getTransactionReceipt',[h]); tx=rpc('eth_getTransactionByHash',[h])
        print(json.dumps(dict(hash=h,block=int(r['blockNumber'],16),status=int(r['status'],16),selector=tx['input'][:10],gas_used=int(r['gasUsed'],16),gas_price=int(r['effectiveGasPrice'],16),actor_net=net(r['logs'],ACTOR),executor_net=net(r['logs'],EXEC),beneficiary_net=net(r['logs'],BENEFICIARY))))
