import subprocess, json
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
MKTS={'cbBTC/USDC':'0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836',
'cbXRP/USDC':'0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109',
'cbETH/USDC':'0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d',
'bsdETH/eUSD':'0xf9ed1dba3b6ba1ede10e2115a9554e9c52091c9f1b1af21f9e0fecc855ee74bf',
'cbADA/USDC':'0xd7520ad198b497b6eb75bc690268f4597630dbc12e305e9d4105843bab36e41d',
'WETH/USDC':'0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda'}
def rpc(method, params):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','base',method,json.dumps(params)],
        capture_output=True, text=True)
    return json.loads(out.stdout)['result']
res={}
for name, mid in MKTS.items():
    data='0x2c3c9157'+mid[2:]
    r=rpc('eth_call',[{'to':MORPHO,'data':data},'latest'])[2:]
    w=[r[i*64:(i+1)*64] for i in range(len(r)//64)]
    res[name]={'loan':'0x'+w[0][-40:],'coll':'0x'+w[1][-40:],'oracle':'0x'+w[2][-40:],'lltv':int(w[4],16)/2**96}
    print(name, json.dumps(res[name]))
toks=sorted({res[n][k] for n in res for k in ('loan','coll')})
dec={}
for t in toks:
    try:
        d=int(rpc('eth_call',[{'to':t,'data':'0x313ce567'},'latest']),16)
    except Exception:
        d=None
    dec[t]=d
    print('decimals', t, d)
res['_decimals']=dec
json.dump(res, open('/srv/farm/ws/scratch/lead383_params.json','w'), indent=1)
