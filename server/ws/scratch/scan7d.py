import subprocess, json, sys
latest=134622849
FROM=latest-272270
addrs=["0xa275769Fb6fF34A1a01C8CE61D0182f5d36AD27A","0x5162f992EDF7101637446ecCcD5943A9dcC63A8A","0x449256e20ac3ed7f9ae81c2583068f7508d15c02","0x61f864a7dfe66cc818a4fd0baabe845323d70454","0x215b3616730020a7f3e075526588d0cdaa057dca","0x36e04b29169313d93a056289109ba8a8291e69ab","0xbc42fadcc37994c65a559fb7803ed60d90994e9f","0xf8af8659a2af27d65bb3e705f0e97b321886031d","0x830e287ac5947b1c0da865dfb3afd7cdf7900464"]
total=0; per={}; logs=[]
b=FROM
while b<=latest:
    e=min(b+4999, latest)
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','bsc','eth_getLogs',json.dumps([{"fromBlock":hex(b),"toBlock":hex(e),"address":addrs}])],capture_output=True,text=True)
    try:
        r=json.loads(p.stdout)['result']
    except Exception as ex:
        print('ERR', b, p.stdout[:120], p.stderr[:120]); b=e+1; continue
    for lg in r:
        total+=1; per[lg['address'].lower()]=per.get(lg['address'].lower(),0)+1
        if len(logs)<40: logs.append((lg['blockNumber'],lg['address'][:10],lg['topics'][0][:20] if lg['topics'] else ''))
    if r: print(f'{b}-{e}: {len(r)}')
    b=e+1
print('TOTAL', total); print(json.dumps(per,indent=0)); print('sample:', logs[:15])
