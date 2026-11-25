import json
rows = json.load(open('/srv/farm/ws/scratch/rc-cvx-delay.json'))
best = {}
for r in rows:
    if r['pool'] and r['caller_crv'] > best.get(r['pool'], 0):
        best[r['pool']] = r['caller_crv']
pools = [p for p, _ in sorted(best.items(), key=lambda kv: -kv[1])][:20]
spec = {"id": "convex.reward_added", "protocol": "convex_finance", "kind": "scheduled_earmark_lump",
        "chains": {"ethereum": pools}, "event": "RewardAdded(uint256)",
        "topic0": "0xde88a922e0d3b88b24e9623efeb464919c6bf9f66857a65e2bfcf2ce87a9433d",
        "indexed": [], "data": ["reward_crv_raw"], "actor_field": "tx_from"}
json.dump(spec, open('/srv/farm/ws/scratch/convex-reward-added-source.json', 'w'), indent=1)
print(len(pools), sum(best[p] for p in pools))
