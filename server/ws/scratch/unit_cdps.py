import json, subprocess
def rpc(method, params):
    out = subprocess.run(['python3','tools/rpc.py','ethereum',method,json.dumps(params)],capture_output=True,text=True).stdout
    r = json.loads(out)
    if 'error' in r: return f'ERROR {r["error"]}'
    return r['result']
# struct CDP {address asset; address owner;} assumed -> decode raw
raw = rpc('eth_call',[{'to':'0x1a5Ff58BC3246Eb233fEA20D32b79B5F01eC650c','data':'0x5a5fdfe5'},'latest'])
h = raw[2:]
arr_len = int(h[64:128],16)
print('cdp count decoded:', arr_len)
words = [h[i:i+64] for i in range(0,len(h),64)]
# layout: offset, len, then structs (asset, owner)
pairs = []
for i in range(arr_len):
    a = '0x'+words[2+2*i][-40:]
    o = '0x'+words[3+2*i][-40:]
    pairs.append((a,o))
# check liquidationBlock for each
liq = []
for a,o in pairs[:60]:
    data = '0x1ce4b4a7'+a[2:].rjust(64,'0')+o[2:].rjust(64,'0')
    r = rpc('eth_call',[{'to':'0xb1cFF81b9305166ff1EFc49A129ad2AfCd7BCf19','data':data},'latest'])
    v = int(r,16)
    if v: liq.append((a,o,v))
print('pending liquidations (liquidationBlock != 0):', len(liq))
for x in liq[:10]: print('  ', x)
print('first 3 pairs:', pairs[:3])
import pickle; pickle.dump(pairs, open('scratch/unit_pairs.pkl','wb'))
