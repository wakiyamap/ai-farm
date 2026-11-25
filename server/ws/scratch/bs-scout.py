import json, urllib.request, os, sys
def get(url):
    req=urllib.request.Request(url, headers={'user-agent':'farm-scout'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())
for q in ['MowerMinter','Mower','ConvexMower']:
    try:
        r=get(f"https://eth.blockscout.com/api/v2/search?q={q}")
        items=r.get('items',[])
        print(q, len(items), [ (i.get('name'), i.get('main_type'), i.get('hash','?')[:14] if i.get('hash') else i.get('address','?')[:14]) for i in items[:5]])
    except Exception as e:
        print(q, 'ERR', e)
