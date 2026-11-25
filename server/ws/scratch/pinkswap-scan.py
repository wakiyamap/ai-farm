import subprocess, json, collections
FR, TO, STEP = 133290000, 134633649, 4800
topics = {
 "0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15":"Deposit",
 "0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568":"Withdraw",
 "0xbb757047c2b5f3974fe26b7c10f732e7bce710b0952a71082702781e62ae0595":"EmergencyWithdraw",
}
addr="0xe981676633dCf0256Aa512f4923A7e8DA180C595"
cnt=collections.Counter(); errs=0; logs=[]
a=FR
while a<=TO:
    b=min(a+STEP-1,TO)
    out=subprocess.run(['python3','tools/rpc.py','bsc','eth_getLogs',json.dumps([{"address":addr,"fromBlock":hex(a),"toBlock":hex(b)}])],capture_output=True,text=True).stdout
    try:
        r=json.loads(out)
        if 'result' in r:
            for L in r['result']:
                t=L['topics'][0].lower()
                cnt[topics.get(t,t) if t in topics else t[:18]]+=1
                logs.append(L)
        else: errs+=1; print("ERR",a,r.get('error',{}).get('message','')[:80],flush=True)
    except Exception as e: errs+=1; print("PARSE-ERR",a,out[:80],flush=True)
    a=b+1
print("chunks errors:",errs)
print("counts:",dict(cnt),"total",sum(cnt.values()))
open('scratch/pinkswap-staking-logs.json','w').write(json.dumps(logs))
