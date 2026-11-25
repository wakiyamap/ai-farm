import json, subprocess
NODES=["https://polygon-bor-rpc.publicnode.com","https://polygon.llamarpc.com"]
VAULT="0xdf16adaf80584b2723f3ba1eb7a601338ba18c4e"
SIG="0x8433ea22"
def arg(h): return h[2:].rjust(64,'0') if h.startswith('0x') else h
DATA=SIG+arg(hex(10**30))+"0"*64+"0"*60+"dead"+"0"*63+"1"
def call(node,blk):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":VAULT,"data":DATA},hex(blk)]})
    p=subprocess.run(["curl","-s","-m","40","-H","Content-Type: application/json","-X","POST",node,"-d",body],capture_output=True,text=True)
    try: d=json.loads(p.stdout)
    except Exception: return "BADJSON",p.stdout[:120]
    if "error" in d:
        e=d["error"]; return "ERR",(str(e.get("message"))[:80]+"|"+str(e.get("data"))[:100])
    r=d["result"]
    return "OK",r[:80] if r else "(empty)"
for node in NODES:
    for blk,note in [(97325849,"B of 80.91 take -> OK expected"),(97325848,"B-1 -> REVERT expected")]:
        print(node.split('//')[1][:22], blk, note, "=>", *call(node,blk))
