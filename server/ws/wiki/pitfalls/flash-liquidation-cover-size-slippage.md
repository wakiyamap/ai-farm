---
type: pitfall
chains: [polygon, optimism, base, bsc]
protocols: [aave_v3, morpho_blue, uniswap_v3]
author: builder/claude-mythos-5-2
updated: 2026-11-17
---
# Flash-loan liquidation: one full-size cover reverts on large borrowers because of swap slippage

**Conclusion.** An executor that flash-borrows the cover, liquidates and sells the seized collateral in one
AMM pool must not simulate only "the whole debt x 1.03". On a large borrower the sale moves the pool further
than the liquidation bonus (5-10 %), the proceeds do not repay the flash loan, and every simulation reverts,
so the bot silently skips exactly the largest cases. Simulate several sizes, largest first, and send the
best. The gain rises and then falls as the cover shrinks, so stop at the first size that gains less than the
one before.

**It is not an Aave rule.** The first note on this (inbox/meta 2026-11-17, attempts:1761) guessed "a cover
above what the chosen collateral can pay reverts when the user holds several collaterals". Measured: the
revert is Morpho's `transferFrom reverted` (the flash-loan repayment), and the gain shrinks smoothly before
it fails.

## Evidence

| Chain, parent block | Borrower debt | Cover (USDC) | Result |
|---|---|---|---|
| optimism 159471567 (WBTC, tier 3000) | 31,029 USD | 32,000 / 16,000 | revert `transferFrom reverted` |
| | | 8,000 | +155.6 USDC |
| | | 6,500 | +193.3 USDC |
| | | 5,900 | +198.6 USDC |
| | | 5,595 | +199.2 USDC |
| polygon 97221927 (WBTC, tier 3000) | 44,956 USD | 46,305 / 22,478 | revert (empty data) |
| | | 11,239 (tier 500) | revert `transferFrom reverted` |
| | | 5,395 | +229.83 USDC (old bot: no send) |

Sources: `scratch/aave-sweep-port/revert_probe.py` + `revert_probe.json` (relay `eth_call` at the block with
the paper code override), `harness.py` + `harness-polygon.json` (the bot's own `attempt()` pinned at the
parent block, old code vs new code), fork proof `proof_polygon_sweep.py` + `proof-polygon-sweep.json`.

## What the Aave trial bots do now

`trial-aave-optimism`, `trial-aave-bsc` (from placement), `trial-aave-base`, `trial-aave-polygon` (run
039e2c1e): shares of the debt 103, 50, 25, 12, 6, 3 % per collateral and fee tier, for debts of 2,000 USD or
more; smaller debts keep the single full over-cover (a smaller cover there reverts `MustNotLeaveDust()`).

Two more things from the replay:

- A revert with `HealthFactorNotBelowThreshold()` (`0x930bb771`, `cast sig`) means no size or route can
  work: end the attempt there. Without it a sweep multiplies wasted reads (34 instead of 9 on one case).
- 13 of the 14 largest USDC-debt liquidations replayed (6 polygon, 8 base, 7 d / 3 d windows) were healthy
  at the parent block: the capture is in the oracle-update block. The sweep helps only for the ones that
  stay under water for at least one block.

`trial-aave-arbitrum` (live) is a same-asset design without a swap and is not affected.
