import json, subprocess

def rpc(m,p):
    o=subprocess.run(['python3','tools/rpc.py','base',m,json.dumps(p)],capture_output=True,text=True).stdout
    try: d=json.loads(o)
    except Exception: return {'__raw__': o[:300]}
    return d.get('result', d)

def sig(s):
    return subprocess.run(['cast','sig',s],capture_output=True,text=True).stdout.strip().split()[0]

def ev(s):
    return subprocess.run(['cast','keccak',s],capture_output=True,text=True).stdout.strip()

HUB="0x783251f103555068c1e9d755f69458f39ed937c0"
BIGV="0xb98840b22618e77bbd0403c81365eefc7d449559"
V2="0x1baeb82f78f55c793296e7153f2b45396ceaeb4b"
FRESH="0x00000000000000000000000000000000BEEF0001"

# hub event topic0s (canonical sigs)
hub=json.load(open('scratch/hub_abi.json'))['abi']
want={}
for e in hub:
    if e.get('type')=='event':
        c=e['name']+"("+",".join(i['type'] for i in e['inputs'])+")"
        want[ev(c)[:10]]=c
print("hub event topic0 prefixes:", {k:v for k,v in list(want.items())})

# read the two most recent hub logs in full
for f,t in [(45000000,50405573),(35000000,45000000)]:
    r=rpc('eth_getLogs',[{'address':HUB,'fromBlock':hex(f),'toBlock':hex(t)}])
    if isinstance(r,list):
        for l in r[-2:]:
            print(hex(int(l['blockNumber'],16)), l['address'], l['transactionHash'],
                  want.get(l['topics'][0][:10], l['topics'][0][:10]), [x for x in l['topics'][1:]], l['data'])

# getters
print("numMarkets:", rpc('eth_call',[{'to':HUB,'data':sig('numMarkets()')},'latest']))
print("protocolFeeClaimant:", rpc('eth_call',[{'to':HUB,'data':sig('protocolFeeClaimant()')},'latest']))
print("vault name:", rpc('eth_call',[{'to':BIGV,'data':sig('name()')},'latest']))
print("vault asset:", rpc('eth_call',[{'to':BIGV,'data':sig('asset()')},'latest']))
print("vault owner:", rpc('eth_call',[{'to':BIGV,'data':sig('owner()')},'latest']))
print("vault totalAssets:", rpc('eth_call',[{'to':BIGV,'data':sig('totalAssets()')},'latest']))
print("vault rewards(0):", rpc('eth_call',[{'to':BIGV,'data':sig('rewards(uint256)')+'0'*64},'latest']))
print("vault2 name:", rpc('eth_call',[{'to':V2,'data':sig('name()')},'latest']))
print("vault2 asset:", rpc('eth_call',[{'to':V2,'data':sig('asset()')},'latest']))

# eth_call reward fns from a fresh address
f0='0'*24
for fn in ['claim(address)','claimFees(address)','ownerClaim(address)','currentUserRewards(address,address)']:
    d=sig(fn)+FRESH[2:].lower().rjust(64,'0')
    if fn=='currentUserRewards(address,address)':
        d=sig(fn)+BIGV[2:].lower().rjust(64,'0')+FRESH[2:].lower().rjust(64,'0')
    r=rpc('eth_call',[{'from':FRESH,'to':BIGV,'data':d},'latest'])
    print(f"BIGV {fn} from fresh:", json.dumps(r)[:200])

# executeWithdrawalScript on the hub from fresh, with a wallet-looking arg
for cand in ["0x10a1bca416313725daeaf4eb0478c0c00d34eb52"]:
    d=sig('executeWithdrawalScript(address)')+cand[2:].lower().rjust(64,'0')
    print("hub executeWithdrawalScript(vault-as-arg):", json.dumps(rpc('eth_call',[{'from':FRESH,'to':HUB,'data':d},'latest']))[:200])

# feeClaimantToTokenToAmount for the fresh address (should be 0) and totals
WETH="0x4200000000000000000000000000000000000006"
d=sig('feeClaimantToTokenToAmount(address,address)')+FRESH[2:].lower().rjust(64,'0')+WETH[2:].lower().rjust(64,'0')
print("hub feeClaimantToTokenToAmount(fresh,WETH):", json.dumps(rpc('eth_call',[{'to':HUB,'data':d},'latest']))[:120])

# gas price
print("gasPrice:", rpc('eth_gasPrice',[]))
