import json,subprocess,sys
def call(to,data,block="latest"):
    r=subprocess.run(["python3","tools/rpc.py","ethereum","eth_call",'[{"to":"%s","data":"%s"},"%s"]'%(to,data,block)],capture_output=True,text=True)
    try:
        d=json.loads(r.stdout)
    except Exception:
        return None
    if 'error' in d: return {'err':d['error'].get('message','')[:80],'data':d['error'].get('data','')[:130]}
    return d['result']
def word(h,i): return h[2+64*i:2+64*(i+1)]
def addr(h): return '0x'+h[2][-40:]
def slot(a,s):
    r=subprocess.run(["python3","tools/rpc.py","ethereum","eth_getStorageAt",'["%s","%s","latest"]'%(a,s)],capture_output=True,text=True)
    try: return json.loads(r.stdout)['result']
    except Exception: return None
def sig(s):
    return subprocess.run(["/opt/foundry/bin/cast","sig",s],capture_output=True,text=True).stdout.strip()
