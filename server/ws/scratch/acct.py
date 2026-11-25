import json, subprocess, sys
CAND='0xed989ee258ecc93769a8478c9973667b17462dfe'
T0='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
def rpc(method, params):
    out = subprocess.run(['python3','tools/rpc.py','base',method,json.dumps(params),'--lane','research'],capture_output=True,text=True)
    if out.returncode!=0: raise SystemExit('rpc fail: '+out.stdout[:200]+out.stderr[:200])
    return json.loads(out.stdout)['result']
def a(t): return '0x'+t[-40:].lower()
txs = sys.argv[1:]
tot={}
for h in txs:
    r=rpc('eth_getTransactionReceipt',[h])
    gascost=int(r['gasUsed'],16)*int(r['effectiveGasPrice'],16)
    net={}
    for l in r['logs']:
        if not l['topics'] or l['topics'][0]!=T0: continue
        tok=l['address'].lower(); f=a(l['topics'][1]); t=a(l['topics'][2]); v=int(l['data'],16)
        if f==CAND: net[tok]=net.get(tok,0)-v
        if t==CAND: net[tok]=net.get(tok,0)+v
    ethnet=0
    print(h[:12], 'gasUsed',int(r['gasUsed'],16), 'gasEth %.5f'%(gascost/1e18), 'effGwei %.2f'%(int(r['effectiveGasPrice'],16)/1e9))
    for tok,v in sorted(net.items(), key=lambda x:-abs(x[1])):
        print('   ',tok[:14], '%.6f'%(v/1e6 if tok=='0x833589fcd6edb6e08f4c7c32d4f71b54bda02913' else v/1e9))
