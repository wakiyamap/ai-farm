import json, urllib.request
Q = """
query($cid:Int!,$hf:Float!,$skip:Int!){marketPositions(where:{chainId_in:[$cid],healthFactor_lte:$hf},first:100,skip:$skip){
 pageInfo{countTotal}
 items{healthFactor user{address} state{collateralUsd borrowAssetsUsd} market{marketId collateralAsset{symbol} loanAsset{symbol}}}}}
"""
for cid in (1,8453,42161,137,10,999):
    skip=0; rows=[]
    while True:
        body = json.dumps({"query":Q,"variables":{"cid":cid,"hf":1.0,"skip":skip}}).encode()
        req = urllib.request.Request("https://blue-api.morpho.org/graphql",data=body,
            headers={"Content-Type":"application/json"})
        try:
            d = json.load(urllib.request.urlopen(req,timeout=30))
        except Exception as e:
            print(f"chain {cid}: ERROR {e}"); break
        mp = d.get("data",{}).get("marketPositions") or {}
        items = mp.get("items",[])
        for i in items:
            st=i["state"] or {}
            c=st.get("collateralUsd") or 0; b=st.get("borrowAssetsUsd") or 0
            if c>=40 and b>=40: rows.append(i)
        skip += len(items)
        total = (mp.get("pageInfo") or {}).get("countTotal", skip)
        if skip >= total or not items: break
    print(f"== chain {cid}: coll>=40 & debt>=40 & HF<=1 -> {len(rows)}")
    for i in rows:
        st=i["state"]; m=i["market"]
        print(f"  {m['collateralAsset']['symbol']}/{m['loanAsset']['symbol']} coll${round(st['collateralUsd'],2)} debt${round(st['borrowAssetsUsd'],2)} hf {round(i['healthFactor'] or -1,5)} {i['user']['address']} {m['marketId']}")
