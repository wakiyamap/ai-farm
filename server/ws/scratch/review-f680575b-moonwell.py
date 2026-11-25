import json,subprocess,sys,re,os,time,urllib.request
from pathlib import Path
os.environ['PATH']='/opt/foundry/bin:'+os.environ['PATH']
import castutil
# window-class whale proof candidate (KB lead 18, measured winner's own event):
# block 53265095 liquidation: holder 0x1a7c950a (borrower==holder, mUSDC borrow,
# the measured winner tx 0x61e686eea746bb3b4b2bfaabec9a54fab1886b8d6a8aab3cb40b366d34cecdf9
# repaid exactly 37.065967636 USDC on this position), collateral mWADO 0xde8df9d9
# (underlying WADO 0x0b3e3284, WADO-cf ~0.055 -> the mToken seizes ~19x the
# shortfall), window >= 32 blocks (mw-window-batch.json: liquidatable at blk-32,
# captured at 53265095). The winner sold WADO -> WETH -> USDC on the PancakeV3
# pools 0x792f465e + 0x4a7af46b; this proof reruns that exact route through the
# executor (swap(recipient,bool,int256,uint160,bytes) 0x128acb08, caller-chosen
# 64-byte context abi.encode(token0,token1) proven on the fork by the
# morpho-watcher-base executor).
BLK=53265095
HOLDER='0x1a7c950a8fff56a7cc679b4cbd085f910c1e7234'
BORROW='0xedc817a28e8b93b03976fbd4a3ddbc9f7d176c22'  # mUSDC (borrow underlying USDC: no borrow swap)
COLL='0xde8df9d942d78ede3ca06e60712582f79cfffc64'    # mWADO
USDC='0x833589fcd6edb6e08f4c7c32d4f71b54bda02913'
WETH='0x4200000000000000000000000000000000000006'
WADO='0x0B3e328455C4059EEB9E3f84b5543F74e24e7e1b'
POOL1='0x792f465e0434fb1028ea3bfeb05240cb839c4e04'   # PancakeV3 WADO/WETH fee100 (measured pools.json @ reset 53342668)
POOL2='0x4a7af46bc8abc00048c6c7920a1488daf568366c'
POOL3='0x784e539f15ca2d19449a6311c5dab6cf37d8f1ba'   # PancakeV3 WETH/USDC (the winner's second leg)
OWNER='0x1111111111111111111111111111111111111111'
COMP='0xfbb21d0380bee3312b33c4353c8936a0f13ef26c'
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
SEL='3230da5d' # liquidate(address,address,address,address,address,uint256,uint256,address,bytes,address,bytes,address,bytes)
SEL_SWAP='128acb08'
SEL_CB='fa461e33' # uniswapV3SwapCallback / pancakeV3SwapCallback(int256,int256,bytes)
MIN_LIMIT='0x1000276a4' # winner's sqrtPriceLimit of record (tx 0x61e686ee words 3); MIN_SQRT_RATIO+1 too close for this pool's SPL check # MIN_SQRT_RATIO+1: both target swaps are token0->token1 (decreasing)
UNDR=0x6f307dc3   # underlying()
CASH=0x3b1d21a2   # getCash()
LIQ='0x5ec88c79'  # getAccountLiquidity(address)
def fork(*a):
    r=subprocess.run(['fork',*a],capture_output=True,text=True)
    out=r.stdout.strip()
    if r.returncode: raise SystemExit('fork failed: '+' '.join(a[:3])+' '+out[-200:]+r.stderr[-200:])
    return out
def jreq(m,p):
    rq=urllib.request.Request('http://127.0.0.1:9001',data=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),headers={"content-type":"application/json"})
    d=json.loads(urllib.request.urlopen(rq,timeout=120).read())
    return d.get('result') if 'result' in d else d.get('error')
def call(to,data):
    r=jreq('eth_call',[{"to":to,"data":data},"latest"])
    return r if isinstance(r,str) else None
def h64(x): return x[2:].lower().rjust(64,'0')
def bal(token,addr):
    r=call(token,'0x70a08231'+h64(addr))
    return int(r[2:],16) if isinstance(r,str) else None
def top_reason(tr):
    return tr.get('revertReason') if isinstance(tr,dict) else None
def send(to,data):
    tx=json.dumps({"from":OWNER,"to":to,"data":data,"gas":"0x30d000","gasPrice":"0x"+hex(10**9+int(time.time()))[2:],"value":"0x0"})
    for i in range(3):
        try:
            out=fork('send','base',tx)
        except SystemExit as e:
            # fork send waits 30s for the receipt; the tx may still mine late -
            # extract the hash from the 'no receipt for 0x..' message and keep polling.
            h=re.search(r'no receipt for (0x[0-9a-f]{64})',str(e))
            if not h: raise
            out='no receipt for '+h.group(1)
        h=re.search(r'"transactionHash":\s*?\s*"(0x[0-9a-f]{64})',out) or re.search(r'no receipt for (0x[0-9a-f]{64})',out)
        h=h.group(1) if h else None
        if not h: raise SystemExit('fork send no hash: '+out[-150:])
        for k in range(120):
            rc=jreq('eth_getTransactionReceipt',[h])
            if rc: return int(rc['status'],16),int(rc['gasUsed'],16),h
            time.sleep(0.5)
        print('send retry',i,'no receipt for',h)
    raise SystemExit('fork send never got a receipt')
def trace(h):
    return jreq('debug_traceTransaction',[h,{"tracer":"callTracer"}])
def pad(a): return a[2:].lower().rjust(64,'0')
def swap_data(exec_,limit,t0,t1):
    # the morpho-watcher-base proven layout: SEL + recipient + zeroForOne(true)
    # + amountSpecified(placeholder, overwritten by the contract) + limit +
    # offset 0xa0 + length 0x40 + token0 + token1; 260 bytes total.
    return '0x'+SEL_SWAP+pad(exec_)+hex(1)[2:].rjust(64,'0')+hex(0)[2:].rjust(64,'0')+ \
        limit[2:].rjust(64,'0')+hex(0xa0)[2:].rjust(64,'0')+hex(0x40)[2:].rjust(64,'0')+pad(t0)+pad(t1)
def run_phase(tag,minprofit,maxrepay=60000000):
    fork('reset','base',str(BLK-1)); fork('fund','base',OWNER,'2')
    LIQR=call(COMP,'0x'+LIQ[2:]+h64(HOLDER))
    w=[int(LIQR[2:][i*64:(i+1)*64],16) for i in range(3)] if isinstance(LIQR,str) else None
    assert w is not None and w[0]==0, 'liquidity read failed: '+repr(LIQR)
    print(tag,'probe (error,liquidity,short 1e18USD):',w[0],round(w[1]/1e18,2),round(w[2]/1e18,2))
    UND=call(COLL,'0x'+f'{UNDR:08x}')
    UND='0x'+UND[2:][-40:] if isinstance(UND,str) else None
    globals()["UND"]=UND
    cash=call(COLL,'0x'+f'{CASH:08x}')
    cash=int(cash[2:],16) if isinstance(cash,str) else None
    print(tag,'coll underlying',UND,'mWADO cash USDC 1e6',cash)
    assert UND=='0x'+WADO[2:].lower(), 'unexpected collateral underlying: '+repr(UND)
    assert cash and cash>=100000000, 'mWADO market cash too thin for the redeem: '+repr(cash)
    HEX=json.load(open('contracts/out/MoonwellWhale.sol/MoonwellWhale.json'))['bytecode']['object']
    CTOR=castutil.abi('constructor(address,address,address,address,address,address,address)',[COMP,MORPHO,USDC,POOL1,POOL2,POOL3,'0x4dbdcb087992404ea9b14fa83cc695b02797f39a'])[2:]
    open('exec.hex','w').write(HEX+CTOR)
    txh=jreq('eth_sendTransaction',[{'from':OWNER,'data':HEX+CTOR,'gas':hex(6000000)}])
    rc=None
    for _ in range(120):
        rc=jreq('eth_getTransactionReceipt',[txh])
        if rc: break
        time.sleep(0.5)
    assert rc and rc['status']=='0x1',repr(rc)
    ex=rc['contractAddress']
    runtime=jreq('eth_getCode',[ex,'latest'])
    expected=Path('/srv/farm/ws/bots/paper/moonwell-whale-base/executor-runtime.hex').read_text().strip()
    assert runtime.lower()==expected.lower(),'submitted runtime mismatch'
    print(tag,'executor',ex)
    # swap1 sells WADO (token0) to WETH: context = abi.encode(token0=WADO, token1=WETH)
    S1=swap_data(ex,MIN_LIMIT,WADO,WETH)
    S2=swap_data(ex,MIN_LIMIT,WETH,USDC)  # context (token0=WETH, token1=USDC)
    ARGS=[HOLDER,HOLDER,BORROW,COLL,UND,str(maxrepay),str(minprofit),'0x0000000000000000000000000000000000000000','0x',POOL1,S1,POOL2,S2]
    DATA='0x'+SEL+castutil.abi('f(address,address,address,address,address,uint256,uint256,address,bytes,address,bytes,address,bytes)',ARGS)[2:]
    ub0=bal(USDC,ex)
    print(tag,'usdc before',ub0/1e6)
    st,gu,h=send(ex,DATA)
    ub1=bal(USDC,ex)
    tr=trace(h) or {}
    print(tag,'tx',h,'status',st,'gasUsed',gu,'revert',top_reason(tr),'usdc after',ub1/1e6)
    return st,gu,h,ub0,ub1,ex,tr
fork('lease','base','15','review f680575b Moonwell WADO fork proof')
try:
    st,gu,h,ub0,ub1,ex,tr=run_phase('success',1000000)
    profit=round((ub1-ub0)/1e6,6)
    print('success profit usd',profit)
    # Guard floor = measured success profit + 0.01 USD margin + 1 wei. borrowBalanceCurrent
    # accrues per second, so each reset phase's profit drifts ~+-0.002 USD with the phase's
    # own block timestamp (measured across runs); a plain +1 floor could be undercut by the
    # guard phase's own (higher) profit and succeed. 0.01 USD covers the observed drift.
    GUARD_MIN=int(profit*1e6)+10001
    st2,gu2,h2,uc0,uc1,ex2,tr2=run_phase('guard',GUARD_MIN)
    st3,gu3,h3,ue0,ue1,ex3,tr3=run_phase('eligibility',1,0)
    r2=top_reason(tr2); r3=top_reason(tr3)
    print('guard tx',h2,'status',st2,'reason',r2,'usdc after guard',uc1/1e6)
    print('eligibility tx',h3,'status',st3,'reason',r3)
    ok=(st==1 and profit>=1 and profit<1500 and st2==0 and r2=='NO_PROFIT' and uc1==uc0 and st3==0 and r3=='NOT_LIQUIDATABLE')
    json.dump({'block':BLK,'reset_block':BLK-1,'account':HOLDER,'holder':HOLDER,'borrowMkt':BORROW,'coll':COLL,
      'underlying':UND,
      'swap_route':'WADO -> WETH (PancakeV3 pool 0x792f465e fee100) -> USDC (PancakeV3 pool 0x4a7af46b), the measured winner route of tx 0x61e686ee',
      'borrow_route':'none (borrow underlying is USDC; no borrow swap)',
      'window_blocks':'>=32 (liquidatable at blk-32 per mw-window-batch.json, captured at block '+str(BLK)+')',
      'maxRepay_usd':60,
      'success':{'tx':h,'status':st,'gasUsed':gu,'usdc_before':ub0/1e6,'usdc_after':ub1/1e6,'profit_usd':profit},
      'guard':{'tx':h2,'status':st2,'gasUsed':gu2,'revert_reason':r2,'usdc_after':uc1/1e6,'minProfit_usd':GUARD_MIN/1e6,'floor_note':'measured success profit +0.01 USD accrual-drift margin +1 wei (borrowBalanceCurrent accrues per second; phase profits drift ~+-0.002 USD)'},
      'eligibility':{'tx':h3,'status':st3,'revert_reason':r3},
      'executor':ex,'proof_ok':bool(ok),'fork_reset_block':BLK-1,'fork_generation_after':'see fork status'},open('/srv/farm/ws/scratch/review-f680575b-moonwell.json','w'),indent=1)
    print('PROOF_OK',bool(ok))
finally:
    fork('release','base')
