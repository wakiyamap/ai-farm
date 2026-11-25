import json, urllib.request, subprocess, sys, time
URL='http://127.0.0.1:9001'
def rpc(m,p=[]):
    req=urllib.request.Request(URL, json.dumps({'jsonrpc':'2.0','id':1,'method':m,'params':p}).encode(), headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(req))['result']
def bal(tok, holder):
    data='0x70a08231'+'000000000000000000000000'+holder[2:]
    r=rpc('eth_call',[{'to':tok,'data':data},'latest'])
    return 0.0 if r=='0x' else int(r,16)/10**18
def native(holder): return int(rpc('eth_getBalance',[holder,'latest']),16)/10**18
TOK={'RSR':'0xab36452dbac151be02b16ca17d8919826072f64a','bsdETH':'0xcb327b99ff831bf8223cced12b1338ff3aa322ff','WETH':'0x4200000000000000000000000000000000000006','USDC':'0x833589426a77970e69c974e7badf3e23e44f4b00','AERO':'0x940181a94a35a4569e4529a3cdfb74e38fd98631','hyUSD':'0xcc7ff230365bd730ee4b352cc2492cedac49383e'}
def snap(h, toks):
    s={'nativeETH': native(h)}
    for t in toks: s[t]=bal(TOK[t],h)
    return s
AG1='0x9008d19f58aabd9ed0d60971565aa8510560ab41'
AG2='0x1636a167cd54f50f73999580d0e3e3a3aeff0001'  # placeholder, set from tx.to below
AG2=None
FILLS=[
 ('B AERO 53487672', 53487671, '0xbd6aedd248ad9eec71c943017126a94f2ddc078f', '0x8b1bd6e6487d52d22383980ba1e398d8fe1b9ec1', ['AERO','RSR','WETH','USDC','hyUSD'], '0x2945aeaeb8c5b13f0ca4788e880d30fca218c25b09ab090d9017fc331ca81800'),
 ('C hyUSD 53490303', 53490302, '0xbd6aedd248ad9eec71c943017126a94f2ddc078f', '0x8b1bd6e6487d52d22383980ba1e398d8fe1b9ec1', ['hyUSD','RSR','WETH','USDC','AERO'], '0x1b070f00902e353425349038c58978b49ba821ad9ddf4dbd834139c1ab297ca7'),
]
out={}
for name, pre_blk, winner, agent, toks, tx in FILLS:
    subprocess.run(['fork','reset','base',str(pre_blk)],capture_output=True); time.sleep(0.5)
    if agent is None:
        agent=rpc('eth_getTransactionByHash',[tx])['result']['to']
    holder=agent
    pre=snap(holder,toks); pre_eoa=native(winner)
    subprocess.run(['fork','replay','base',tx],capture_output=True); time.sleep(0.5)
    post=snap(holder,toks); post_eoa=native(winner)
    diff={k:post[k]-pre[k] for k in pre}; diff['EOA_ETH_gas']=post_eoa-pre_eoa; diff['EOA_ETH']=post_eoa-pre_eoa if False else post_eoa-pre_eoa
    out[name]={'winner':winner,'agent':agent,'pre':pre,'diff':diff}
    print(name,'agent',agent)
    for k in pre: print(f"   {k:8s} {pre[k]:>18.6f} -> {post[k]:>18.6f}  diff {diff[k]:+.6f}")
json.dump(out, open('scratch/rb-netdiff.json','w'), indent=1)
