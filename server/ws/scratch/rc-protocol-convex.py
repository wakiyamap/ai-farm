import json, subprocess
row = json.loads(subprocess.run(['kb', 'query', '--json', "SELECT checked FROM protocols WHERE id=147 LIMIT 1"],
                                capture_output=True, text=True).stdout.strip().splitlines()[0])
add = (" 2026-11-12 run ce71d6eb (attempt 987, lead 156): Booster.earmarkRewards caller incentive measured (the earmark leg was not covered by 592/596/599). earmarkIncentive 50 bps; 7d: 905 earmark txs, ~163k CRV/day earmarked, ~800 CRV/day to callers. ~90% of that is weekly lumps gated by a stash reward hook (reverts crvChange until crvRewards.periodFinish+3600), taken in the first eligible block at index 0-1 by ~10 searchers who pay 99.7-99.9% to block.coinbase (3/3 traces). The rest is continuous earmarks at gas break-even. Not takeable. Ledger source convex.reward_added installed. Wiki infra/convex-earmark-builder-auction.md.")
json.dump({'checked': row['checked'] + add, 'wiki_page': 'infra/convex-earmark-builder-auction.md'},
          open('/srv/farm/ws/scratch/kb-protocol-convex.json', 'w'))
print(len(row['checked']), len(row['checked'] + add))
