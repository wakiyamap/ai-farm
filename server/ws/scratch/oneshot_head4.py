import json, urllib.request
Q = """
query($cid:Int!,$hf:Float!,$skip:Int!){marketPositions(where:{chainId_in:[$cid],healthFactor_lte:$hf},first:100,skip:$skip){
 itemCount items{user{address}state{collateralUsd borrowAssetsUsd healthFactor}market{marketId collateralAsset{symbol} loanAsset{symbol}}}}}
"""
for cid in (1,8453,42161,137,10,999):
    skip=0; farm=[]; total=0
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
        total = mp.get("itemCount", 0)
        for i in items:
            st=i["state"] or {}
            if st.get("borrowAssetsUsd") and st["borrowAssetsUsd"]>=50: farm.append(i)
        skip += len(items)
        if skip >= total or not items: break
    print(f"chain {cid}: HF<=1 itemCount={total} farm-size(>=50USD debt)={len(farm)}")
    for i in farm[:25]:
        st=i["state"]; m=i["market"]
        print("  ", m["collateralAsset"]["symbol"],"/",m["loanAsset"]["symbol"],
              "coll$",round(st.get("collateralUsd") or 0,2),"debt$",round(st["borrowAssetsUsd"],2),
              "hf",round(st.get("healthFactor") or -1,3), i["user"]["address"][:12], m["marketId"][:12])
