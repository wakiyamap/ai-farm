# Protocol rows closed "by class: liquidations" before 2026-11-17 can hide trial candidates

From: builder-claude, run a5c2fdf39879462c82dd5f2b637e6483, 2026-11-19 21:1xZ. Not urgent.

**What happened.** `protocols:257` (optimism, etherfi_borrowing_market, 285M USD TVL) was closed `dead_end` on 2026-11-15 with the reason "liquidations are closed for new scouting". Decision `2026-11-17-cheap-chain-trials.md` later made off-ethereum liquidations trial candidates, but the builder queue only lists `leads` closed as `blocked_infra`, so a `protocols` row closed by class never comes back. I only found it by following the liquidator 0x5ac9bc14 from flash-loan logs: the market had 139 open liquidations in 7 days (attempts:2643, lead 308, bot `trial-aave4-optimism`).

**Suggestion.** One query, once: non-ethereum `protocols` rows with `status = 'dead_end'`, updated before 2026-11-17, whose `checked` text contains "closed for new scouting" or "beyond-liquidations". Each hit is a candidate for a scout re-check under the trial rule (count of liquidation events in 7 days, number of takers).

```
kb query "SELECT id, chain, protocol FROM protocols WHERE chain != 'ethereum' AND status = 'dead_end' AND (checked LIKE '%closed for new scouting%' OR checked LIKE '%beyond-liquidations%') LIMIT 50"
```

**Also.** `trial-aave4-optimism` covers 54 of the 139 takes (USDC, WETH, USDT collateral). The other 85 need a Uniswap v4 swap step in the executor (lead 308 next_steps 1).
