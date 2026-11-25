import subprocess, json
MORPHO='0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
MKTS=['0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836',
'0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109',
'0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d',
'0xf9ed1dba3b6ba1ede10e2115a9554e9c52091c9f1b1af21f9e0fecc855ee74bf',
'0xd7520ad198b497b6eb75bc690268f4597630dbc12e305e9d4105843bab36e41d',
'0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda']
def rpc(method, params):
    p=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','base',method,json.dumps(params)],
        capture_output=True, text=True)
    try: return json.loads(p.stdout)
    except Exception: return {'err':p.stdout[:200]+p.stderr[:200]}
# raw 5-word market params
words={}
for m in MKTS:
    r=rpc('eth_call',[{'to':MORPHO,'data':'0x2c3c9157'+m[2:]},'latest'])['result'][2:]
    words[m]=[r[i*64:(i+1)*64] for i in range(5)]
def liq_calldata(m, borrower, repaid):
    d='0xd8eabcb8'+''.join(words[m])
    d+=borrower[2:].lower().rjust(64,'0')
    d+='0'*64  # seizedCollateral = 0
    d+=format(int(repaid),'064x')
    d+='%064x'%(5*32+3*32)  # offset of bytes after 5+3 head words? heads: 5(mkt)+1 borrower+1 seized+1 repaid =8 words -> offset 8*32=256
    d+='%064x'%(10*32)
    d+='%064x'%(0)   # hmm fix below
    return d
# simpler: heads = market(5)+borrower+seized+repaid+offset = 8 words -> offset = 8*32 = 256
def calldata(m, borrower, repaid):
    d='0xd8eabcb8'+''.join(words[m])
    d+=borrower[2:].lower().rjust(64,'0')
    d+='0'*64
    d+=format(int(repaid),'064x')
    d+='%064x'%(8*32)
    d+='%064x'%0      # bytes length 0
    return d
def probe(m, borrower, repaid, block):
    r=rpc('eth_call',[{'from':'0x1111111111111111111111111111111111111111','to':MORPHO,'data':calldata(m,borrower,int(repaid))},hex(block)])
    if 'result' in r: return 'SUCCESS'
    msg=r.get('error',{}).get('message','') or str(r.get('err',''))
    if 'healthy' in msg.lower(): return 'healthy'
    return 'takeable:'+msg[:60]
sample=json.load(open('/srv/farm/ws/scratch/lead383_gross.json'))
events=[]
seen=set()
for r in sample['top']+sample['recent']:
    k=(r['tx_hash'],r['log_index'])
    if k in seen: continue
    seen.add(k); events.append(r)
events=events[:15]
out=[]
blocks={}
for e in events:
    row={'block':e['block'],'tx':e['tx_hash'][:14],'log':e['log_index'],'ts':e['ts'],
         'mkt':e['mkt'][:10],'caller':e['caller'],'borrower':e['borrower'],'repaid':e['repaid'],
         'seized':e['seized'],'gross':round(e['gross'],4)}
    rc=rpc('eth_getTransactionReceipt',[e['tx_hash']])
    rec=rc.get('result') or {}
    row['status']=rec.get('status'); row['gasUsed']=int(rec.get('gasUsed','0x0'),16) if rec.get('gasUsed') else None
    egp=int(rec.get('effectiveGasPrice','0x0'),16) if rec.get('effectiveGasPrice') else None
    efp=int(rec.get('maxPriorityFeePerGas','0x0'),16) if rec.get('maxPriorityFeePerGas') else None
    b=blocks.get(e['block'])
    if b is None:
        br=rpc('eth_getBlockByNumber',[hex(e['block']),False])
        bb=br.get('result') or {}
        b={'baseFee':int(bb.get('baseFeePerGas','0x0'),16),'ts':int(bb.get('timestamp','0x0'),16)}
        blocks[e['block']]=b
    row['baseFee_gwei']=round(b['baseFee']/1e9,4)
    if egp is not None:
        row['effGasPrice_gwei']=round(egp/1e9,4)
        row['tip_gwei']=round(max(0,egp-b['baseFee'])/1e9,4)
        row['winner_gas_usd']=round(rec['gasUsed'] if isinstance(rec.get('gasUsed'),int) else int(rec['gasUsed'],16),1)
    row['maxPrio_gwei']=round((efp or 0)/1e9,4)
    # takeable walk
    if e is sample['top'][0] or any(e['tx_hash']==t['tx_hash'] and e['log_index']==t['log_index'] for t in sample['top']):
        p=probe(e['mkt'],e['borrower'],e['repaid'],e['block'])
        row['probe_at_capture']=p[:40]
    # full walk for top5; bounded for others
    walk = 15
    steps=[]
    bb=e['block']-1; first_healthy=None; calls=0
    while bb>=e['block']-walk and calls<walk:
        pr=probe(e['mkt'],e['borrower'],e['repaid'],bb); calls+=1
        if pr=='healthy': first_healthy=bb; break
        bb-=1
    row['probe_calls']=calls
    if first_healthy is None:
        row['takeable_blocks_before_capture']='>%d'%walk if calls>=walk else str(calls+1)+'?'
    else:
        row['takeable_blocks_before_capture']=e['block']-first_healthy-1
    out.append(row)
    print(json.dumps(row), flush=True)
json.dump(out, open('/srv/farm/ws/scratch/lead383_probe_out.json','w'), indent=1)
