import json, subprocess, sys
CAND='0xed989ee258ecc93769a8478c9973667b17462dfe'
T0='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
def rpc(method, params):
    out = subprocess.run(['python3','tools/rpc.py','base',method,json.dumps(params),'--lane','research'],capture_output=True,text=True)
    if out.returncode!=0: raise SystemExit('rpc fail: '+out.stdout[:200]+out.stderr[:200])
    return json.loads(out.stdout)['result']
dec={}
def getdec(tok):
    if tok in dec: return dec[tok]
    try:
        r=rpc('eth_call',[{'to':tok,'data':'0x313ce567'},'latest'])
        dec[tok]=int(r,16) if r and r!='0x' else None
    except Exception: dec[tok]=None
    return dec[tok]
def sym(tok):
    try:
        r=rpc('eth_call',[{'to':tok,'data':'0x95d89b41'},'latest'])
        h=r[2:]
        n=int(h[:64],16)*2 if len(h)>=64 and int(h[:64],16)<=32 else 0
        return bytes.fromhex(h[64:64+n]).decode('latin1') if n else '?'
    except Exception: return '?'
def a(t): return '0x'+t[-40:].lower()
h=sys.argv[1]
r=rpc('eth_getTransactionReceipt',[h])
print('gasUsed',int(r['gasUsed'],16),'effGwei %.3f'%(int(r['effectiveGasPrice'],16)/1e9))
inn={}; out={}
for l in r['logs']:
    if not l['topics'] or l['topics'][0]!=T0: continue
    tok=l['address'].lower(); f=a(l['topics'][1]); t=a(l['topics'][2]); v=int(l['data'],16)
    if f==CAND: out[tok]=out.get(tok,0)+v
    if t==CAND: inn[tok]=inn.get(tok,0)+v
for tok in set(list(inn)+list(out)):
    d=getdec(tok) or 18
    print(sym(tok), tok[:14], 'IN %.4f'%(inn.get(tok,0)/10**d), 'OUT %.4f'%(out.get(tok,0)/10**d))
