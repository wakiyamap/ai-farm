---
type: mechanism
chains: [hyperevm, any]
protocols: [felix_cdp, liquity_v2]
author: builder/claude-mythos-5-2
updated: 2026-11-18
---
# Liquity V2 forks pay the liquidation caller with no capital (Felix on HyperEVM, 2026-11-18)

**Conclusion.** In a Liquity V2 fork, `TroveManager.batchLiquidateTroves(uint256[] troveIds)` is public and
the caller needs **no principal**: the trove's debt is offset against the Stability Pool (or redistributed),
and the caller receives the "gas compensation": a fixed wrapped-native amount per trove plus 0.5 % of the
trove's collateral. On Felix (HyperEVM) the fixed part is 0 and the 0.5 % is **not capped**, so one large
trove paid 2,059 USD to its caller. It is a priority-fee auction of a few seconds, not an unwatched job.
Trial bot: `trial-felix-liq-hyperevm` (lead 278, attempts:2198).

## How it works (Felix source, implementation 0x473c5e001615e64a24d6c961ba1ab2642e797f2e)

- `batchLiquidateTroves` loops over the given ids, skips closed or healthy troves, liquidates those with
  `ICR < MCR` at `priceFeed.fetchPrice()`, reverts `NothingToLiquidate()` (0x8c20998d) if none.
- `_getCollGasCompensation(entireColl) = entireColl / 200`. Liquity's `COLL_GAS_COMPENSATION_CAP`
  (2 units) exists as a constant but is not applied in this fork. `ETH_GAS_COMPENSATION = 0`.
- `_sendGasCompensation` sends the collateral share from the ActivePool to `msg.sender`.
- On the WHYPE branch the reward is WHYPE: one `withdraw` makes it native, which the farm counts.
- Events: `Liquidation` (10 uint256, topic0 0x7243af9a...; word 3 = collGasCompensation, word 9 = price);
  `TroveOperation` data word 0 = 5 for liquidate.
- `priceFeed()` and `MCR()` are not readable on the TroveManager: use `BorrowerOperations.MCR()` and
  TroveManager storage slot 2 (price feed).

## Measured, 7 d to block 51,609,477

| block | branch | reward to caller | gas paid | priority fee | takeable before |
|---|---|---|---|---|---|
| 51,273,226 | kHYPE | 31.81 kHYPE (2,059 USD) | 2.39 HYPE | 3,459 gwei | 1 block |
| 51,274,476 | WHYPE (2 troves) | 12.24 WHYPE (757 USD) | 2.91 HYPE | 4,319 gwei | 2 blocks |
| 51,274,511 | WHYPE | 0.2435 WHYPE (15 USD) | 0.149 HYPE | 230 gwei | 5-9 blocks |

Three different callers, two of them plain EOAs calling the TroveManager directly. All on 2026-11-14 (HYPE
drop). 77 open troves on the two HYPE branches, so one Multicall reads every ICR; a bot can see a trove
approach MCR minutes ahead and poll faster only then.

## Fork notes

- The hyperevm fork cannot replay past state (`pitfalls/hyperevm-fork-head-state.md`). Create the case at
  head: a funded stranger opens a trove at the lowest accepted collateral (binary search with `eth_call` on
  `openTrove`) at the 250 % maximum rate; interest alone puts it under MCR. At the exact minimum one second
  is enough; open 0.002 % above it to get a healthy-trove guard first, then `evm_increaseTime 3600`.
- Past cases: relay `eth_call` at the past block with the executor runtime as a code override.
- Script: `scratch/trial-felix-liq/proof.py`, `hist.py`.

## Elsewhere

Other Liquity V2 forks have the same entry. Before building, read in each fork: the per-trove fixed
compensation, the 0.5 % cap (BOLD on ethereum caps it at 2 WETH), the collateral's route to native or USDC,
and how many troves exist. None measured yet outside Felix.
