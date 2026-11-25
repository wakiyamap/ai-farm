import json, subprocess, datetime

def rpc(m,p):
    o=subprocess.run(['python3','tools/rpc.py','base',m,json.dumps(p)],capture_output=True,text=True).stdout
    try: d=json.loads(o)
    except Exception: return {'__raw__': o[:300]}
    return d.get('result', d)

def sel(s):
    return subprocess.run(['cast','sig',s],capture_output=True,text=True).stdout.strip().split()[0]

def ev(s):
    return subprocess.run(['cast','keccak',s],capture_output=True,text=True).stdout.strip()

def addr(h): return '0x'+h[-40:]

HUB="0x783251f103555068c1e9d755f69458f39ed937c0"
VMH="0xa97ecc6bfda40baf2fdd096dd33e88bd8e769280"
PF="0x19112adbdafb465ddf0b57ecc07e68110ad09c50"
WVF="0x75e502644284edf34421f9c355d75db79e343bca"
FRESH="0x00000000000000000000000000000000BEEF0001"
HEAD=60930588; W7=57906587

# hub custom errors
hub=json.load(open('scratch/hub_abi.json'))['abi']
errs={}
for e in hub:
    if e.get('type')=='error':
        c=e['name']+"("+",".join(i['type'] for i in e['inputs'])+")"
        errs[sel(c)[:10]]=c
print("hub errors:", errs)

# real Weiroll wallets from past WeirollWalletExecutedWithdrawal logs
wallets=["0x889091ff0df25ee57e319131927932c608090375","0x54c8177e23b9ada427b53e01248239a481a1b040","0xa9755589e1b21ed40ace5be0e9ed7b5aafeab5e4"]
for w in wallets:
    d=sel('executeWithdrawalScript(address)')+w[2:].lower().rjust(64,'0')
    r=rpc('eth_call',[{'from':FRESH,'to':HUB,'data':d},'latest'])
    print("EWS", w, "->", json.dumps(r)[:160])
    print("   code:", json.dumps(rpc('eth_getCode',[w,'latest']))[:60], " amount:", json.dumps(rpc('eth_call',[{'to':w,'data':sel('amount()')},'latest']))[:80])

# other protocol contracts 7d log counts
for name,a in [("RecipeMarketHub",HUB),("VaultMarketHub",VMH),("PointsFactory",PF),("WrappedVaultFactory",WVF)]:
    r=rpc('eth_getLogs',[{'address':a,'fromBlock':hex(W7),'toBlock':hex(HEAD)}])
    print(f"7d logs {name}: {len(r) if isinstance(r,list) else json.dumps(r)[:120]}")

# control: same shape on active base contract, 5k blocks
r=rpc('eth_getLogs',[{'address':'0x833589fcd6edb6e08f4c7c32d4f71b54bda02913','fromBlock':hex(HEAD-5000),'toBlock':hex(HEAD)}])
print("control USDC 5k blocks:", len(r) if isinstance(r,list) else json.dumps(r)[:120])

# vault reward pots: rewardToInterval on the 4 funded vaults + reward token list
VAULTS=["0xb98840b22618e77bbd0403c81365eefc7d449559","0x1baeb82f78f55c793296e7153f2b45396ceaeb4b","0x8cd82a50f1168e61b88f6f92ace198c0059fec73","0xded00ff949d611b9ee91ab1a086e81ecfc23bd76"]
for v in VAULTS:
    ta=rpc('eth_call',[{'to':v,'data':sel('totalAssets()')},'latest'])
    print(v, "totalAssets", int(ta,16) if isinstance(ta,str) else ta)
    for i in range(2):
        rt=rpc('eth_call',[{'to':v,'data':sel('rewards(uint256)')+'%064x'%i},'latest'])
        print("   rewards(%d)"%i, json.dumps(rt)[:100])
