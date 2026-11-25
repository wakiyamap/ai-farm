import json, subprocess, collections, sys

# tx hashes + liquidation counts from ledger
out = subprocess.run(["ledger","query","--json","SELECT tx_hash, COUNT(*) n, MAX(block) blk, MAX(ts) ts FROM events WHERE source_id='morpho_blue.liquidate' AND chain='base' AND actor='0x5451c4b4ea335bfb71f75316594bb68d26d30917' GROUP BY tx_hash"],capture_output=True,text=True).stdout
rows=[json.loads(l) for l in out.strip().splitlines() if l.strip()]
print("txs:", len(rows), "liq:", sum(r['n'] for r in rows))

ETH_USD = 1815.0  # DefiLlama coins.llama.fi coingecko:ethereum 2026-11-16

# owner USDC inflow per tx via getLogs (already saved)
logs=json.load(open('/srv/farm/ws/scratch/owner-in-usdc.json'))['result']
profit={}
for lg in logs:
    h=lg['transactionHash']
    profit[h]=profit.get(h,0)+int(lg['data'],16)/1e6

days=collections.defaultdict(lambda: dict(liq=0,txs=0,gas=0.0,prof=0.0))
missing=[]
tot=dict(gas=0.0,prof=0.0)
for r in rows:
    rec=subprocess.run(["python3","/srv/farm/ws/tools/rpc.py","base","eth_getTransactionReceipt",'["%s"]'%r['tx_hash'],"--lane","research"],capture_output=True,text=True).stdout
    try:
        j=json.loads(rec)['result']
    except Exception:
        missing.append(r['tx_hash']); continue
    gu=int(j['gasUsed'],16); gp=int(j['effectiveGasPrice'],16)
    g=gusd=gu*gp/1e18*ETH_USD
    p=profit.get(r['tx_hash'],0.0)
    import datetime
    d=datetime.datetime.utcfromtimestamp(r['ts']).strftime('%m-%d')
    dd=days[d]; dd['liq']+=r['n']; dd['txs']+=1; dd['gas']+=g; dd['prof']+=p
    tot['gas']+=g; tot['prof']+=p
print("day       liq txs   gas$   profit$   net$   net/liq")
for d in sorted(days):
    dd=days[d]
    print(f"{d} {dd['liq']:5d} {dd['txs']:3d} {dd['gas']:8.2f} {dd['prof']:9.2f} {dd['prof']-dd['gas']:8.2f} {(dd['prof']-dd['gas'])/dd['liq']:7.3f}")
print(f"TOTAL gas ${tot['gas']:.2f} profit ${tot['prof']:.2f} net ${tot['prof']-tot['gas']:.2f} over {len(rows)} txs, missing {len(missing)}")
# per-tx stats
per=[(profit.get(r['tx_hash'],0.0)) for r in rows]
per.sort()
print("profit per tx: median", per[len(per)//2], "max", per[-1], "min", per[0])
