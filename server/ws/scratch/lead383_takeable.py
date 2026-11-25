import subprocess, json
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
def rpc(method, params):
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','base',method,json.dumps(params)],
        capture_output=True, text=True)
    try: return json.loads(p.stdout)['result']
    except Exception: return None
params={}
def market_words(m):
    if m not in params:
        r=rpc('eth_call',[{'to':MORPHO,'data':'0x2c3c9157'+m[2:]},'latest'])
        params[m]=[r[2:][i*64:(i+1)*64] for i in range(5)]
    return params[m]
def is_liq(m, borrower, block):
    d='0x59b674b2'+m[2:]+borrower[2:].lower().rjust(64,'0')+''.join(market_words(m))
    r=rpc('eth_call',[{'to':MORPHO,'data':d},hex(block)])
    if r is None: return None
    return r[-1]=='1'
samples=json.load(open('/srv/farm/ws/scratch/lead383_probe_out.json'))
calls=0
for s in samples:
    C=s['block']; m=s['mkt_full'] if 'mkt_full' in s else s['mkt']
    mid={'0x9103c3b4':'0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836',
         '0x8793cf30':'0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda',
         '0xd4a903dc':'0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109',
         '0x0ca10126':'0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d',
         '0xf9ed1dba':'0xf9ed1dba3b6ba1ede10e2115a9554e9c52091c9f1b1af21f9e0fecc855ee74bf',
         '0xd7520ad1':'0xd7520ad198b497b6eb75bc690268f4597630dbc12e305e9d4105843bab36e41d'}[s['mkt']]
    b=s['borrower']
    ok=C-1
    v=is_liq(mid,b,C-1); calls+=1
    s['liq_at_C_minus_1']=v
    left=C-1500
    vl=is_liq(mid,b,left); calls+=1
    if vl is None or v is None:
        s['takeable_first_block']='rpc-fail'; print(json.dumps(s)); continue
    if not v:
        s['takeable_first_block']='not-takeable-at-C-1'; print(json.dumps(s)); continue
    if vl:
        s['takeable_first_block']='<%d'%left; s['takeable_blocks_before_capture']='>=1500'; print(json.dumps(s)); continue
    lo,hi=left,C-1
    while lo+1<hi:
        midb=(lo+hi)//2
        if is_liq(mid,b,midb): hi=midb
        else: lo=midb
        calls+=1
    s['takeable_first_block']=hi
    s['takeable_blocks_before_capture']=C-1-hi
    print(json.dumps(s), flush=True)
print('total probe calls', calls)
json.dump(samples, open('/srv/farm/ws/scratch/lead383_takeable.json','w'), indent=1)
