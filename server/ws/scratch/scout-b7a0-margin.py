"""Sample this filler's txs: entry selector, tx.from, net ERC20 flows of filler/EOA, gas."""
import json, subprocess, sys, collections
FILLER='0xb7a0d4608cd7831102498f0c49a8212cfd32ee9b'
TR='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
def rpc(m,p):
    r=subprocess.run(['python3','/srv/farm/ws/tools/rpc.py','bsc',m,json.dumps(p),'--lane','research'],capture_output=True,text=True)
    if r.returncode: print('ERR',m,r.stderr[:200]); sys.exit(1)
    return json.loads(r.stdout)['result']
rows=subprocess.run(['ledger','query','--json',"SELECT block, tx_hash, ts, fields FROM events WHERE chain='bsc' AND source_id='uniswapx.fill' AND actor='%s' ORDER BY block DESC LIMIT 60" % FILLER],capture_output=True,text=True).stdout
evs=[json.loads(l) for l in rows.strip().split('\n') if l.strip()]
print('events pulled:', len(evs))
import datetime
picks=[]
step=max(1,len(evs)//12)
for i in range(0,len(evs),step):
    picks.append(evs[i])
for e in picks[:12]:
    tx=rpc('eth_getTransactionByHash',[e['tx_hash']]); rc=rpc('eth_getTransactionReceipt',[e['tx_hash']])
    net=collections.defaultdict(lambda: collections.defaultdict(int))
    for x in rc['logs']:
        if x['topics'][0]==TR and len(x['topics'])==3:
            a=x['address'].lower(); f_='0x'+x['topics'][1][-40:].lower(); t_='0x'+x['topics'][2][-40:].lower()
            v=int(x['data'],16) if x['data']!='0x' else 0
            for who in (FILLER, tx['from'].lower()):
                if f_==who: net[who][a]-=v
                if t_==who: net[who][a]+=v
    gas=int(rc['gasUsed'],16)*int(rc['effectiveGasPrice'],16)/1e18
    f=json.loads(e['fields'])
    print(json.dumps({"tx":e['tx_hash'][:16],"blk":e['block'],"ts":datetime.datetime.utcfromtimestamp(e['ts']).isoformat(),
      "from":tx['from'],"to":tx['to'],"sel":tx['input'][:10],"status":rc['status'],
      "gasUsed":int(rc['gasUsed'],16),"gwei":round(int(rc['effectiveGasPrice'],16)/1e9,4),"gas_bnb":round(gas,6),
      "val_eth":round(int(tx['value'],16)/1e18,6),"swapper":f['swapper'],
      "filler_net":{k[:10]:v for k,v in net[FILLER].items() if v},
      "eoa_net":{k[:10]:v for k,v in net[tx['from'].lower()].items() if v}}))
