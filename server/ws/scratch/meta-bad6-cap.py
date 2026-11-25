import json, sys
d = json.load(open(sys.argv[1]))
inter = sum(d["intermediate_balances_usd"].values())
live = sum(sum(b["balances_usd"].values()) for b in d["live"].values())
print("intermediate", round(inter, 2), "live", round(live, 2), "sum", round(inter + live, 2), "capital_usd", d["capital_usd"], "n_live", len(d["live"]))
