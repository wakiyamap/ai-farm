import json, urllib.request, os
URL=os.environ['RPC_RELAY_URL']; LANE='research'
def rpc(chain, method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(f"{URL}/{chain}?lane={LANE}", data=body, headers={"content-type":"application/json"})
    r=json.loads(urllib.request.urlopen(req, timeout=60).read())
    if 'error' in r: return ('ERR', r['error'].get('message','')[:200])
    return ('OK', r['result'])
TOPIC0="0x7dfecd8419723a9d3954585a30c2a270165d70aafa146c11c1e1b88ae1439064"
facades={
 'arbitrum': ["0x"+"1908d57f8e71a4199dd73d12fe7d0455d086fef5","0x"+"db2f856815b2ab329622d69600f40b6111f3746d","0x"+"12855c0430604ff69c02c27e5a8b1e2ab9d955fb","0x"+"f9e2fa1df473a0f8d4933dae82f341fcddde03ea","0x"+"eaa9471931ed27d3d377e340940176f0d7f449af","0x"+"08f640d53a7ace42eb5aeef512103a708882bb14"],
 'optimism': ["0x"+"60beb4ee5396f059e3c169bd3303b688b0a3eb26","0x"+"e2cac6f006940d482724add3c0fd67379b612feb","0x"+"5e51b1bbb78b7b30b73bcd2e58a08f2a7e315339","0x"+"92198c1d20705e40a4b201a14b5543db6a316285","0x"+"448c5d57c6f83bebbdc8b7bbc90ac7f57ee00d8c","0x"+"469af4272429d54eb04da564f06860d978649277"],
}
span={'arbitrum': 6_000_000, 'optimism': 2_600_000}
report={}
for chain,addrs in facades.items():
    st,head=rpc(chain,'eth_blockNumber',[])
    head=int(head,16); fromB=head-span[chain]
    st,bh=rpc(chain,'eth_getBlockByNumber',[hex(fromB),False])
    if st!='OK': print(chain,'block read fail',bh); continue
    from_ts=int(bh['timestamp'],16)
    st,bh2=rpc(chain,'eth_getBlockByNumber',[hex(head),False])
    head_ts=int(bh2['timestamp'],16)
    days=(head_ts-from_ts)/86400
    st,logs=rpc(chain,'eth_getLogs',[{"address":addrs,"topics":[TOPIC0],"fromBlock":hex(fromB),"toBlock":hex(head)}])
    if st!='OK': print(chain,'getlogs fail',logs); continue
    liq={}
    for lg in logs:
        liq['0x'+lg['topics'][1][26:].lower()]=liq.get('0x'+lg['topics'][1][26:].lower(),0)+1
    report[chain]=dict(head=head, fromB=fromB, days=days, n_logs=len(logs),
        events_per_day=len(logs)/days if days else 0,
        liquidators={k:v for k,v in sorted(liq.items(), key=lambda x:-x[1])},
        blocks=[int(l['blockNumber'],16) for l in logs],
        accounts=[ '0x'+l['topics'][0][26:] for l in logs],
        first_ts=from_ts, head_ts=head_ts,
        log_txs=[l['transactionHash'] for l in logs])
    print(chain, f"head={head} range={fromB}..{head} days={days:.1f} logs={len(logs)} per_day={len(logs)/days:.2f}")
    print(' liquidators:', report[chain]['liquidators'])
json.dump(report, open('scratch/gbx-census.json','w'), indent=1)
