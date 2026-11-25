import json
d = json.load(open("/srv/farm/ws/scratch/review-gate-after-72849.json"))
stopped = open("/srv/farm/ws/scratch/meta-bad6-stopped.txt").read().split()
out = {}
for b in stopped:
    v = d["live"][b]
    chains = [c for c in v["balances_usd"] if ":" not in c]
    assert len(chains) == 1, (b, chains)
    out[b] = [v["address"], chains[0]]
json.dump(out, open("/srv/farm/ws/scratch/meta-bad6-addrs.json", "w"), indent=1)
print(len(out))
