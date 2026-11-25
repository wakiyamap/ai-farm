#!/usr/bin/env python3
import subprocess, sys, json
# usage: call.py <to> <sig> [argsjson] [from]
to=sys.argv[1]; sig=sys.argv[2]
args=json.loads(sys.argv[3]) if len(sys.argv)>3 else []
frm=sys.argv[4] if len(sys.argv)>4 else None
sel=subprocess.run(['cast','sig',sig.split('(')[0]+'('+sig.split('(')[1].split(')')[0]+')'],capture_output=True,text=True).stdout.strip()
if not sel: print('no selector'); sys.exit(1)
data=sel
if args:
    fn,sigs=sig.split('('); plist=sigs.rstrip(')').split(',') if sigs.rstrip(')') else []
    data=subprocess.run(['cast','calldata',sig]+[json.dumps(a) if not isinstance(a,str) else a for a in args],capture_output=True,text=True).stdout.strip()
    if not data: print('calldata fail'); sys.exit(1)
tx={'to':to,'data':data}
if frm: tx['from']=frm
p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','bsc','eth_call',json.dumps([tx,'latest'])],capture_output=True,text=True)
try:
    r=json.loads(p.stdout)
    if 'error' in r: print('REVERT', json.dumps(r['error'])[:300]); sys.exit(0)
    print(r['result'])
except Exception as e:
    print('ERR', p.stdout[:300], p.stderr[:200])
