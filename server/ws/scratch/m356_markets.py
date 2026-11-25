import json, subprocess
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
IDS=["0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836",
"0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d",
"0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109",
"0x09276541cfecb6920a80679a1deced4dde3ae64bf5fc2c9c1f9c21e0c152e1a5",
"0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda",
"0xe458a501c1103ca3b256f2bcb45d223263fb34b6349d82675494ce3a94ce1327",
"0x9125d0fa03c3137166df68bcc72283477830de2a4a5536512374c573ad4583c3"]
def rpc(method, params):
    p=subprocess.run(['python3','tools/rpc.py','base',method,json.dumps(params)],capture_output=True,text=True)
    if not p.stdout: raise RuntimeError(p.stderr)
    return json.loads(p.stdout)['result']
def call(to,data,blk='latest'):
    return rpc('eth_call',[{'to':to,'data':data},blk])
out={}
toks={}
for mid in IDS:
    r=call(MORPHO,'0x2c3c9157'+mid[2:])
    loan=r[2:66]; coll=r[66:130]; oracle=r[130:194]
    loan='0x'+loan[-40:]; coll='0x'+coll[-40:]; oracle='0x'+oracle[-40:]
    out[mid]={'loan':loan,'coll':coll,'oracle':oracle}
    toks[loan]=None; toks[coll]=None
for t in toks:
    try:
        sym=call(t,'0x95d89b41'); sym=bytes.fromhex(sym[10:]).decode(errors='replace')
    except Exception as e: sym='ERR'
    dec=int(call(t,'0x313ce567'),16)
    toks[t]=(sym,dec)
for mid,v in out.items():
    print(mid[:10], toks[v['loan']], toks[v['coll']], 'oracle',v['oracle'][:10])
print(json.dumps({'markets':out,'tokens':{k:list(v) for k,v in toks.items()}}))
