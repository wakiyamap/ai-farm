import json, subprocess
NODE="https://polygon-bor-rpc.publicnode.com"
VAULT="0xdf16adaf80584b2723f3ba1eb7a601338ba18c4e"
DATA="0x8433ea22"+hex(10**30)[2:].rjust(64,'0')+"0"*64+"0"*24+"dead"+"0"*32+"0"*63+"0"
def call(to,data,blk):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},hex(blk)]})
    p=subprocess.run(["curl","-s","-m","40","-H","Content-Type: application/json","-X","POST",NODE,"-d",body],capture_output=True,text=True)
    try: d=json.loads(p.stdout)
    except Exception: return("BADJSON",p.stdout[:100])
    if "error" in d:
        e=d["error"]; msg=e.get("message","")
        datax=e.get("data","")
        if isinstance(datax,dict): datax=datax.get("data") or datax.get("revertReason") or json.dumps(datax)
        return("REVERT", (msg+"|"+str(datax))[:120])
    return("OK", str(d["result"])[:80])
tests=[(VAULT,97325848,"B-1 of 80.91 take, expect REVERT"),
       (VAULT,97325849,"B of 80.91 take, expect OK"),
       (VAULT,97322802,"B-1 of exception 0xd7b188d7, expect OK"),
       (VAULT,97322801,"B-2 of exception, expect REVERT")]
head=json.loads(subprocess.run(["curl","-s","-m","20","-H","Content-Type: application/json","-X","POST",NODE,"-d",'{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}'],capture_output=True,text=True).stdout)["result"]
print("head",int(head,16))
print("head probe:",call(VAULT,DATA,int(head,16)))
for to,blk,note in tests:
    s,m=call(to,DATA,blk); print(blk,note,"->",s,m)
