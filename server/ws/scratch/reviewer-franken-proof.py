#!/usr/bin/env python3
"""Paper-reviewer replay: insert compiled runtime without mining a deploy block."""
import json, subprocess, urllib.request, time

FORK = 'http://127.0.0.1:9003'
RELAY = 'http://127.0.0.1:8545/ethereum?lane=paper'
CAST = '/opt/foundry/bin/cast'
OWNER = '0x1111111111111111111111111111111111111111'
EXEC = '0x8f7a45ebde059392e46a46dcc14ab24681a961ea'
HUB = '0xDE12B620A8a714476A97EfD14E6F7180Ca653557'
USDC = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
ZCHF = '0xb58e61c3098d85632df34eecfb899a1ed80921cb'
USDT = '0xdac17f958d2ee523a2206206994597c13d831ec7'
P1 = '0x3416cf6c708da44db2624d63ea0aaef7113527c6'
P3 = '0x8e4318e2cb1ae291254b187001a59a1f8ac78cef'
TOKENS = {8: ('0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640'),
          9: ('0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf', '0x4548280ac92507c9092a511c7396cbea78fa9e49'),
          10: ('0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640')}
WINS = {8: 26293524, 9: 26311563, 10: 26327481}
CODE = open('/srv/farm/ws/bots/paper/franken-threshold-ethereum/state/executor-code.hex').read().strip()

def rpc(url, method, params):
    req = urllib.request.Request(url, data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(), headers={'Content-Type':'application/json'})
    ans = json.loads(urllib.request.urlopen(req,timeout=180).read())
    if 'error' in ans: raise RuntimeError(str(ans['error']))
    return ans['result']

def sel(sig):
    return subprocess.check_output([CAST,'keccak',sig],text=True).strip()[2:10]

def call(to,data):
    return rpc(FORK,'eth_call',[{'from':OWNER,'to':to,'data':data},'latest'])

def bal(token, addr):
    return int(call(token,'0x'+sel('balanceOf(address)')+addr[2:].zfill(64)),16)

def allowance(token, owner, spender):
    return int(call(token,'0x'+sel('allowance(address,address)')+owner[2:].zfill(64)+spender[2:].zfill(64)),16)

def encode(num,size,maxoffer,token,exitpool,minprofit,deadline):
    return subprocess.check_output([CAST,'calldata','bid(uint32,uint256,uint256,address,address,address,address,uint256,uint256)',str(num),str(size),str(maxoffer),token,exitpool,P1,P3,str(minprofit),str(deadline)],text=True).strip()

out = []
for num, winner in WINS.items():
    for offset in (1,0):
        # offset=1: mine at winner-1, one full block ahead; offset=0: mine at winner, same block.
        target = winner-offset
        subprocess.run(['fork','reset','ethereum',str(target-1)],check=True,capture_output=True,text=True)
        rpc(FORK,'anvil_setBalance',[OWNER,hex(5*10**18)])
        rpc(FORK,'anvil_setCode',[EXEC,CODE])
        chain_ts = int(rpc(RELAY,'eth_getBlockByNumber',[hex(target),False])['timestamp'],16)
        rpc(FORK,'evm_setNextBlockTimestamp',[chain_ts])
        challenge = call(HUB,'0x'+sel('challenges(uint256)')+hex(num)[2:].zfill(64))
        words = [int(challenge[i:i+64],16) for i in (2,66,130,194)]
        size = words[3]
        token, exitpool = TOKENS[num]
        price = int(call(HUB,'0x'+sel('price(uint32)')+hex(num)[2:].zfill(64)),16)
        offer = price*size//10**18
        cd = encode(num,size,offer*2+10**18,token,exitpool,1,target+3)
        pre = {'usdc':bal(USDC,OWNER),'exec_usdc':bal(USDC,EXEC),'allow_zchf':allowance(ZCHF,EXEC,HUB)}
        tx = {'from':OWNER,'to':EXEC,'data':cd,'gas':hex(1200000),'gasPrice':hex(int(rpc(FORK,'eth_gasPrice',[]),16)+10**9)}
        h = rpc(FORK,'eth_sendTransaction',[tx])
        rec = None
        for _ in range(40):
            rec = rpc(FORK,'eth_getTransactionReceipt',[h])
            if rec: break
            time.sleep(0.25)
        if not rec: raise RuntimeError('missing receipt')
        row={'num':num,'target':target,'winner':winner,'tx':h,'status':int(rec['status'],16),'mined_block':int(rec['blockNumber'],16),'gas_used':int(rec['gasUsed'],16),'offer_zchf':offer/10**18,'owner_usdc_delta':(bal(USDC,OWNER)-pre['usdc'])/10**6,'allow_zchf_pre':pre['allow_zchf'],'allow_zchf_post':allowance(ZCHF,EXEC,HUB),'exec_usdc_post':bal(USDC,EXEC),'exec_zchf_post':bal(ZCHF,EXEC),'exec_usdt_post':bal(USDT,EXEC),'exec_collateral_post':bal(token,EXEC)}
        if not row['status']:
            trace=rpc(FORK,'debug_traceTransaction',[h,{'tracer':'callTracer'}])
            row['revert_data']=(trace.get('output') or '')[:10]
        out.append(row)
        print(json.dumps(row),flush=True)
with open('/srv/farm/ws/scratch/reviewer-franken-result.json','w') as f: json.dump(out,f,indent=2)
