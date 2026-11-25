import json, urllib.request
Q = """
query($cid:Int!,$hf:Float!){marketPositions(where:{chainId_in:[$cid],healthFactor_lte:$hf},first:100){
 items{user{address}state{collateralUsd borrowAssetsUsd}market{marketId collateralAsset{symbol} loanAsset{symbol}}}}}
"""
for cid in (1,8453,42161,137,10,999):
    body = json.dumps({"query":Q,"variables":{"cid":cid,"hf":1.0}}).encode()
    req = urllib.request.Request("https://blue-api.morpho.org/graphql",data=body,
        headers={"Content-Type":"application/json"})
    try:
        d = json.load(urllib.request.urlopen(req,timeout=30))
    except Exception as e:
        print(f"chain {cid}: ERROR {e}")
        continue
    items = d.get("data",{}).get("marketPositions",{}).get("items",[])
    farm = [i for i in items if (i["state"] or {}).get("borrowAssetsUsd") and i["state"]["borrowAssetsUsd"]>=50]
    print(f"chain {cid}: HF<=1 items={len(items)} farm-size(>=50USD debt)={len(farm)}")
    for i in farm[:25]:
        st=i["state"]; m=i["market"]
        print("  ", m["collateralAsset"]["symbol"],"/",m["loanAsset"]["symbol"],
              "coll$",st.get("collateralUsd"),"debt$",st["borrowAssetsUsd"],
              i["user"]["address"][:10], m["marketId"][:10])
