import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def call(chain, to, data):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"latest"]}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={LANE}", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=30).read())
    if 'error' in r: return ('ERR', r['error'].get('message','')[:120])
    return ('OK', r['result'])
chains={
 'arbitrum': ["0x75bc0fef1c93723be3d73b2000b5ba139a0c680c","0xb4bc02c0859b372c61abccfa5df91b1ccaa4dd1f","0xcedaa4b4a42c0a771f6c24a3745c3ca3ed73f17a","0x3ab1d35500d2da4..."],
}
# re-parse from raw: fetch fresh
import re
def getcm(chain, reg):
    st,res=call(chain, reg, "0x94144856")
    if st!='OK': return None
    hexs=res[2:]
    n=int(hexs[64:128],16)
    addrs=["0x"+hexs[128+i*64+24:128+i*64+64] for i in range(n)]
    return addrs
regs={'arbitrum':'0xc3e00cda97d5779bfc8f17588d55b4544c8a6c47','optimism':'0x949f9899bdadcc7831ca422f115fe61f4211a30b'}
out={}
for chain,reg in regs.items():
    cms=getcm(chain,reg)
    print(chain,'credit managers:',cms)
    facades=[]
    for cm in cms:
        st,res=call(chain,cm,"0x5014a0fb")  # facade()
        if st=='OK' and res and len(res)>=66:
            facades.append((cm, "0x"+res[-40:]))
        else:
            facades.append((cm, st+' '+str(res)[:80]))
    out[chain]=facades
    print(chain,'manager->facade:')
    for m,f in facades: print('  ',m,'->',f)
json.dump(out, open('scratch/pin-facade.json','w'), indent=1)
