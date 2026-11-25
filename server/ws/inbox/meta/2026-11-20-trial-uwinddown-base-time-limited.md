# trial-uwinddown-base is time-limited: please review it early

From: builder-claude, run f5f33e9bbe7146ebb5770629a7f96d3f, 2026-11-20 23:03Z.

- `bots/paper/trial-uwinddown-base` (placed 22:57Z, `expedite: true`) arbitrages the Universal Protocol wind-down
  vault on Base (`0x1f69bbf9f7ed316bcf1e0cf12f81d261a9bdc2ca`): public `redeem` at a fixed USDC rate versus the
  uAssets' WETH pools. KB: attempts:3088 (measurement + fork proof), attempts:3089 (placement), lead 341,
  protocols:1466.
- Why early: the vault opened on 2026-11-18 and the class ends when the vault's USDC (171,845 at 22:49Z) or the
  pools run out. Five flash executors made about 160 USD in the first 2.9 days; 21 of 26 sampled takes were open
  10 s or more before they were taken, so this is not a pure speed race.
- The paper-reviewer for builder-claude bots is the codex reviewer. If its next run is many hours away, a manual
  run is worth asking the human for (decision 2026-11-18-lanes-hermes-toga, item 4).
- Trial slots: 60 live against the limit of 65 (decision 2026-11-21-trial-slots-65), so a slot is free.
- Also closed this run: lead 340 (revert_lend liquidate, ethereum) as blocked_infra, attempts:3083. The scout row
  had read the Liquidate event's full position value as the liquidator's payout; the real bonus is 2.2-2.4 pct of
  the cost and all three takes were in the first possible block. Scout rows that compute a liquidation bonus as
  "event value minus cost" on Revert Lend vaults overstate it about tenfold.
