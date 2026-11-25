import json,urllib.request
root='https://api.github.com/repos/Instadapp/fluid-contracts-public/contents/deployments/bnb'
a=json.load(urllib.request.urlopen(root,timeout=15))
rows=[]
for e in a:
 n=e.get('name','')
 if n.startswith(('VaultT1_','VaultT2_','VaultT3_','VaultT4_')) and n.endswith('.json') and '_Operate' not in n:
  d=json.load(urllib.request.urlopen(e['download_url'],timeout=15))
  rows.append({'name':n[:-5],'address':d['address']})
open('scratch/venus-flux-vaults.json','w').write(json.dumps(rows,indent=2))
print(len(rows)); print('\n'.join(f"{r['name']} {r['address']}" for r in rows))
