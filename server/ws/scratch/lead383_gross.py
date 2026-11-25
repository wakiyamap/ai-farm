import subprocess, json
P={'cbBTC':59170.92782758688/1e8,'cbXRP':0.9164469651349545/1e6,'cbETH':1890.68/1e18,
   'cbADA':0.14137475462870386/1e6,'bsdETH':1846.8759899125655/1e18,'WETH':1655.2203735438293/1e18}
USDC=0.9999858587999999/1e6; EUSD=0.998636351619003/1e18
M={'cbBTC/USDC':'0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836',
'cbXRP/USDC':'0xd4a903dc6d949519060c7707f9604fdc9772c046e05c2e3a8fce0bd7196e4109',
'cbETH/USDC':'0x0ca10126f6c94cbd9cf0a48cc9516ae5e3dec5aa68303e6d988ee37c5149bf0d',
'bsdETH/eUSD':'0xf9ed1dba3b6ba1ede10e2115a9554e9c52091c9f1b1af21f9e0fecc855ee74bf',
'cbADA/USDC':'0xd7520ad198b497b6eb75bc690268f4597630dbc12e305e9d4105843bab36e41d',
'WETH/USDC':'0x8793cf302b8ffd655ab97bd1c695dbd967807e8367a65cb2f4edaf1380ba1bda'}
coll={M['cbBTC/USDC']:P['cbBTC'],M['cbXRP/USDC']:P['cbXRP'],M['cbETH/USDC']:P['cbETH'],
M['bsdETH/eUSD']:P['bsdETH'],M['cbADA/USDC']:P['cbADA'],M['WETH/USDC']:P['WETH']}
inlist="','".join(M.values())
cases=" ".join(f"WHEN '{k}' THEN {v:.6e}" for k,v in coll.items())
base=("WITH e AS (SELECT block, tx_hash, log_index, ts, json_extract(fields,'$.id') mkt, "
 "json_extract(fields,'$.caller') caller, json_extract(fields,'$.borrower') borrower, "
 "CAST(json_extract(fields,'$.repaidAssets') AS REAL) repaid, "
 "CAST(json_extract(fields,'$.seizedAssets') AS REAL) seized "
 "FROM events WHERE chain='base' AND source_id='morpho_blue.liquidate' AND ts>=1794714406 "
 f"AND block>=57620152 AND json_extract(fields,'$.id') IN ('{inlist}')), "
 "g AS (SELECT *, seized*(CASE mkt "+cases+" END) - repaid*(CASE WHEN mkt='"+M['bsdETH/eUSD']+
 f"' THEN {EUSD:.6e} ELSE {USDC:.6e} END) gross FROM e) ")
def q(sql):
    out=subprocess.run(['ledger','query','--json',base+sql],capture_output=True,text=True)
    return [json.loads(l) for l in out.stdout.strip().splitlines() if l.strip()]
top=q("SELECT * FROM g ORDER BY gross DESC LIMIT 5")
recent=q("SELECT * FROM g ORDER BY ts DESC LIMIT 12")
mid=q("SELECT * FROM g ORDER BY gross ASC LIMIT 1 OFFSET 2220")
above=q(f"SELECT count(*) n FROM g WHERE gross > 0.04")
tot=q("SELECT count(*) n, avg(gross) avg, sum(gross) total FROM g")
json.dump({'top':top,'recent':recent,'p50':mid,'above_gas':above,'tot':tot},
 open('/srv/farm/ws/scratch/lead383_gross.json','w'), indent=1)
print('TOP5:'); [print(json.dumps(r)) for r in top]
print('P50:', json.dumps(mid[0]))
print('ABOVE 0.04 USD:', json.dumps(above[0]), 'TOTALS:', json.dumps(tot[0]))
print('RECENT n=',len(recent))
for r in recent: print(json.dumps(r))
