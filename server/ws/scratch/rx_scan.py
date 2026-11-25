import subprocess, json, sys
V="0xb5a30e1fa2cf3c8dea882124b3ab5a47a27c5dd2"
head=0x7fe7f27
start=head-294000
topics={"0x2ae72b44f59d038340fca5739135a1d51fc5ab720bb02d983e4c5ff4119ca7b8":"Skim",
"0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7":"Deposit",
"0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db":"Withdraw",
"0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef":"Transfer",
"0x15c027cc4fd826d986cad358803439f7326d3aa4ed969ff90dbee4bc150f68e9":"UpdateLastTotalAssets",
"0xf66f28b40975dbb933913542c7e6a0f50a1d0f20aa74ea6e0efe65ab616323ec":"AccrueInterest"}
counts={}; evts=[]; errs=0
b=start
while b<=head:
    e=min(b+4999,head)
    out=subprocess.run(["python3","tools/rpc.py","bsc","eth_getLogs",json.dumps([{"fromBlock":hex(b),"toBlock":hex(e),"address":V}]) ,"--lane","research"],capture_output=True,text=True)
    try:
        r=json.loads(out.stdout)
    except Exception:
        errs+=1; b=e+1; continue
    if 'error' in r:
        errs+=1; print("ERR",b,r['error'].get('message','')[:80],file=sys.stderr)
    else:
        for log in r.get('result',[]):
            t=log['topics'][0]
            name=topics.get(t,"other:"+t[:10])
            counts[name]=counts.get(name,0)+1
            if name in ("Skim","Deposit","Withdraw") and len(evts)<40:
                evts.append({"name":name,"block":int(log['blockNumber'],16),"tx":log['transactionHash'],"topics":log['topics'][1:],"data":log['data']})
    b=e+1
print(json.dumps({"counts":counts,"errors":errs,"evts":evts},indent=1))
