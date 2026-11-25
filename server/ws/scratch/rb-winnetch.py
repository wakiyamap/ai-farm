import json, subprocess, urllib.request
URL='http://127.0.0.1:9001'
def rpc(m,p=[]):
    r=urllib.request.urlopen(URL, json.dumps({'jsonrpc':'2.0','id':1,'method':m,'params':p}))
    return json.load(r)
def bal(a, tok=None):
    # native: eth_getBalance; token: balanceOf
    if tok is None: return int(rpc('eth_getBalance',[a,'latest'])['result'],16)/1
    d=rpc('eth_call',[{'to':tok,'data':'0x70a08231'+a[2:] if False else '0x'+'70a08231'+a[2:].zfill(0)[:0]+a[2:],'latest'}]) if False else None
    return d
def balanceOf(token, holder):
    data='0x70a08231'+'000000000000000000000000'+holder[2:]
    r=rpc('eth_call',[{'to':token,'data':data},'latest'])['result']
    return int(r,16)
def reset(b):
    r=urllib.request.urlopen('http://127.0.0.1:9001', json.dumps({'jsonrpc':'2.0','id':1,'method':'anvil_reset','params':[{'forkConfig':{'blockNumber':hex(b)}}]}))
    return json.load(r)
import sys
WIN='0x5c3593481cba011737e36ded62f1797c9f6afce1'
RSR='0xab36452dbac151be02b16ca17d8919826072f64a'
BSD='0xcb327b99ff831bf8223cced12b1338ff3aa322ff'
WETH='0x4200000000000000000000000000000000000006'
USDC='0x833589426a77970e69c974e7badf3e23e44f4b00'
HY='0xcc7ff230365bd730ee4b352cc2492cedac49383e'
def snapshot(h, toks):
    s={ 'ETH': int(rpc('eth_getBalance',[h,'latest'])['result'],16)/10**18 }
    for t in toks: s[t]=balanceOf(t,h)/10**18
    return s
fills=[('A bsdETH bid', 53481595, WIN, WIN, [RSR,BSD,WETH,USDC]),
       ('C hyUSD revenue', 53490302, None, None, None)]
