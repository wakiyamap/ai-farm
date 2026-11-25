#!/usr/bin/env python3
# Control leg on the shared fork (reset 26394057): debtless funded EOA burns
# 5e18 weETH via the manager; assert no cash out, eETH lands on vault leg
# 0x7d57, pool 0x308861a4 totalBorrowed unchanged. Plus pool/vault identity
# reads. (Success leg with a debt-holding borrower stays open - see KB.)
import json, urllib.request
from subprocess import run, PIPE
URL='http://127.0.0.1:9003'
MANAGER='0xfbfe6b9cee0e555bad7e2e7309effc75200cbe38'
WEETH='0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee'
EETH='0x35fa164735182de50811e8e2e824cfb9b6118ac2'
VAULT='0x7d5706f6ef3f89b3951e23e557cdfbc3239d4e2c'
POOL='0x308861a4bb1a71e50490245f577068cc76f36145'
EOA='0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266'
_id=[0]
def rpc(m,p=None):
    body={'jsonrpc':'2.0','id':_id[0],'method':m,'params':p or []}; _id[0]+=1
    req=urllib.request.Request(URL,json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
    r=json.load(urllib.request.urlopen(req))
    if 'error' in r: raise RuntimeError((m,r['error'].get('message')))
    return r['result']
def w(a): return '0'*(64-len(a[2:]))+a[2:]
def u(h): return int(h,16) if h and h!='0x' else 0
def sel(s): return run(['cast','sig',s],capture_output=True,text=True).stdout.strip()
def call(to,data):
    try: return u(rpc('eth_call',[{'to':to,'data':data},'latest']))
    except RuntimeError as e: return ('REVERT' if 'reverted' in str(e.args[1]) else str(e.args[1]))
def sendto(frm,to,data):
    r=rpc('eth_sendTransaction',[{'from':frm,'to':to,'data':data,'gas':'0x90000'}])
    for _ in range(30):
        rc=rpc('eth_getTransactionReceipt',[r])
        if rc: return r,rc
    return r,None
BAL=sel('balanceOf(address)'); APPROVE=sel('approve(address,uint256)'); BURN='0xccc143b8'
U_TOK=sel('underlyingToken()'); U_TB=sel('totalBorrowed()')
def main():
    blk0=rpc('eth_blockNumber',[])
    print('block',blk0)
    print('pool.underlyingToken', hex(call(POOL,U_TOK))[:42] if isinstance(call(POOL,U_TOK),int) else call(POOL,U_TOK))
    print('pool.totalBorrowed', call(POOL,U_TB)/1e18 if isinstance(call(POOL,U_TB),int) else call(POOL,U_TB))
    print('vault.underlyingToken', call(VAULT,U_TOK) if not isinstance(call(VAULT,U_TOK),int) else hex(call(VAULT,U_TOK))[:42])
    tb0=call(POOL,U_TB); bal0=call(WEETH,'0x'+w(EOA)[8:] and ('0x70a08231'+w(EOA)))
    eeth0=call(EETH,'0x70a08231'+w(VAULT)); eth0=int(rpc('eth_getBalance',[EOA,'latest']),16)
    print('pre: pool.totalBorrowed',tb0/1e18,'EOA weETH',bal0/1e18,'vault eETH',eeth0/1e18,'EOA eth',eth0/1e18)
    rpc('anvil_impersonateAccount',[EOA]); rpc('anvil_setBalance',[EOA,'0x'+format(int(1e18),'x')])
    eth0=int(rpc('eth_getBalance',[EOA,'latest']),16)
    txh,rec=sendto(EOA,WEETH,APPROVE+w(MANAGER)+'0x'+'f'*64)
    print('approve',txh,rec['status'])
    txh,rec=sendto(EOA,MANAGER,BURN+'0x'+'%064x'%(5*10**18))
    print('CONTROL BURN tx',txh,'status',rec['status'],'gasUsed',rec['gasUsed'])
    tb1=call(POOL,U_TB); bal1=call(WEETH,'0x70a08231'+w(EOA)); eeth1=call(EETH,'0x70a08231'+w(VAULT)); eth1=int(rpc('eth_getBalance',[EOA,'latest']),16)
    print('post: pool.totalBorrowed',tb1/1e18,'(unchanged:',tb0==tb1,') EOA weETH',bal1/1e18,'vault eETH',eeth1/1e18,'delta eETH',(eeth1-eeth0)/1e18,'EOA eth delta',(eth1-eth0)/1e18)
    print('eETH/weETH parity delivered:',(eeth1-eeth0)/5e18)
    print('fork block end',rpc('eth_blockNumber',[]),'start',blk0)
main()
