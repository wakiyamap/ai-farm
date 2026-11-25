import json, subprocess

def call(to, data):
    p=[{'to':to,'data':data},'latest']
    subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','base','eth_call',json.dumps(p),'--lane','research','--out','/tmp/rc.json'],capture_output=True,text=True)
    d=json.load(open('/tmp/rc.json'))
    if 'error' in d: return None
    res=d['result'][2:]
    if len(res)%64: res='0'*(64-len(res)%64)+res
    return res

def words(res): return [res[i:i+64] for i in range(0,len(res),64)]
def addr(w): return '0x'+w[-40:]

def encode_static(vals): # vals: (int|address|bytes32)
    out=''
    for kind,v in vals:
        if kind=='u': out+=f'{v:064x}'
        elif kind=='a': out+='0'*24+v[2:].lower()
        elif kind=='b': out+=v[2:] if v.startswith('0x') else v
    return out

def decode_addr_array(res):
    w=words(res)
    n=int(w[1],16)
    return [addr(w[2+i]) for i in range(n)]

def decode_string(res):
    w=words(res)
    off=int(w[0],16)//32; n=int(w[off],16)
    return bytes.fromhex(''.join(w[off+1:off+1+(n+31)//32])).decode(errors='replace')
