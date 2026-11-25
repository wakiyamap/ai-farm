import subprocess, json, sys
def call(to,data):
    out = subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','polygon','eth_call',json.dumps([{'to':to,'data':data},'latest'])],capture_output=True,text=True).stdout
    return json.loads(out)['result']
def word(h): return int(h[2:],16)
res={}
for name,vd,cnt in [('PAR','0xde1996189ee1857d79f1f2bebe2a4a2b200bcb44',1381),('paUSD','0x8a604e5c0ced41064354d055b84fc964aaa9101a',24)]:
    act=[]
    for i in range(1,cnt+1):
        d=word(call(vd,'0xd310f49b'+hex(i)[2:].rjust(64,'0')))
        if d>0: act.append(i)
    res[name]=act
    print(name,'active with debt:',len(act),act[:60],flush=True)
json.dump(res,open('scratch/vault_debts.json','w'))
