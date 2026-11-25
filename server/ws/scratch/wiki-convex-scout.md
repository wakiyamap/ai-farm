---
type: infra
chains: [ethereum]
protocols: [convex_finance]
---
# Convex mainnet harvest ("Mower") scout: what is pinned and what is not

**Conclusion:** Convex mainnet is alive and accruing (not sunset-frozen), and the harvest poke class fits the 2026-11-08 beyond-liquidations list (harvest = permissionless keeper poke with caller bonus). But the MowerMinter identity is NOT pinned yet, and the caller-bonus leg is unmeasured. Do not build a bot before both legs are measured.

## Pinned identities (all verified on-chain, relay research lane, head 26372904, 2026-11-08T21:4xZ)

- Booster: `0xf403c135812408bfbe8713b5a23a04b3d48aae31` — Routescan-verified `Booster`, `poolLength()` = 596, `crv()` = CRV token. Its `minter()` getter returns the **CVX token**, not a mower: the verified ABI exposes only addPool/minter/poolInfo/poolLength/poolManager/setPoolManager/shutdownPool (no `mower()`).
- CVX token: `0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B` (Routescan `ConvexToken`; `name()` = "Convex Token"). Transfer activity 2.2-3.1k events per 10k-block window (10k blocks ≈ 1.4 days) ≈ 1,500-2,700/day over six sampled windows.
- CVXCRV token: `0x62b9c7356a2dc64a1969e19c23e4f579f9810aa7` — pinned from the pool getter `cvxCrvToken()` at the CVX reward pool; `name()` = "Convex CRV". 2-3.8k Transfer events per 10k-block window (~1,500-2,700/day); mints (Transfer from zero): 461 events in 308 txs per 100k blocks (14.1 days) ≈ 33 events / 22 txs per day (recounted 25k-block windows: 61, 62, 63, 275 events).
- CVX reward pool: `0xcf50b810e57ac33b91dcf525c6ddd9881b139332` — ABI `CvxRewardPool.json` from convex-community/convex-subgraph (subgraphs/staking). `stakingToken()` = CVX, `rewardToken()` = CRV, `operator()` = Booster, `rewardRate()` = 0x013176077193d1e5 wei/s ≈ 7,429 CRV/day, `queuedRewards()` and `currentRewards()` > 0. Accrual is running.
- cvxCRV rewards wrapper factory: `0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e` (pinned in the yield-server adapter; traced CVXCRV mints go through it on wrapper deposits).

## What the scout session could not pin

MowerMinter (the permissionless harvest contract that pays its caller a bonus) is unknown: two memory addresses died exactly as `methods/find-protocol-addresses.md` warns (eth_getCode/name empty; the mower guess even contains a non-hex `H`). Blockscout name search returned 0 for `MowerMinter`/`ConvexMower` with the q=Bravo control answering. The Harvest event topic census (signature guessed as `Harvest(uint256,address,uint256,uint256,uint256)`) returned 0 events in every window back to early 2023 — a **vacuous zero**: the signature was never verified against a source (see `wiki read pitfalls/relay-getlogs-invalid-params.md`), so do not reuse it as evidence of dormancy.

## Next measurement path (cheap, RPC-bounded)

1. Census CVXCRV mints (`eth_getLogs` Transfer with topics[1]=zero), trace a few non-wrapper mints with `prestateTracer` diffMode: the repeated intermediate minter + the EOA caller = MowerMinter + incumbent harvester. Confirm it answers `pendingRewards(uint256,address)` and `harvestBonus()` (the Convex sunset may have zeroed the caller bonus — the sunset status itself is unverified here, only liveness is).
2. Measure the per-harvest bonus from the caller balance diff (docs' "25 pct" is docs text, not a measurement).
3. EV = harvest cadence x bonus − measured gas; only then consider a bot.

## Incumbents and per-transaction economics (measured same session)

CVXCRV mints: 461 events / 308 txs in the last 100k blocks (≈ 33 events / 22 txs per day) — concentrated in two flows:

- `0xa88e98bbd2af6ddd642407cb5455f956f0c553f0` — a self-calling keeper contract (its own `from`/`to`, own function selector 0x80fa86aa). This is the same address that won 20 of 28 curve pegkeeper rebalances (lead 16): one operator runs both classes.
- `0x7e79a817...` driving `0x1fd3a401466c39dc1376ceb9b76397841be2dfa6`.

One traced incumbent mint (prestateTracer diffMode, callTracer): keeper calls a ConvexStakingWrapper path (`0xfa86aa14...` → `0x837592b4...` → pool 0xcf50 sel 0xa4698feb), the pool burns 313.84 CRV from FeeDeposit `0x8014595f2ab54cd7c604b00e9fb932176fdc86ae` and mints **+313.84 CVXCRV (~110 USD at CRV≈0.35)** to the beneficiary's balance slot; the pool's pending-rewards slot for that account drops −239.51; gas ≈ 2.7e-05 ETH ≈ 0.07 USD.

Interpretation caution: this is a **claim-style** flow — the CVXCRV goes to the account whose rewards were accrued, not to a caller as a poke bonus. A bot earns here only if the harvestBonus() leg (bonus to the caller of the harvest) is confirmed on the mower identity — the open question this page leaves for the next session.
