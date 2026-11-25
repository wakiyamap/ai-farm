---
type: pitfall
chains: [base]
protocols: [morpho_blue]
---
# Morpho Blue liquidation math on base (measured 2026-11-03)

Conclusion first: on the deployed singleton `0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb`,
a liquidation that seizes `S` raw collateral repays exactly
`repaid = ceil(ceil(S * price / 1e36) * 1e18 / incentive)` loan-asset wei, where
`incentive = min(1.15e18, 1e18*1e18 // (1e18 - (0.3e18*(1e18-lltv)//1e18)))` —
**12.676% bonus at lltv 0.625, 4.384% at 0.86**. The oracle price `price()` is
loan-denominated with scale 1e36 (`ORACLE_PRICE_SCALE = 1e36` constant; decimals are the
oracle's job).

Evidence: winner tx `0x2d56cc606a28bfb7d3ac8beb792fe666c6a54a6159d11b3c10d0b0dc063c01c1`
(block 53447309) Liquidate events match the formula to the wei: 13.27293479 cbZEC at oracle
1120.86 → repaid 13203.398612 USDC; 0.41634851 cbZEC → 414.167285 USDC.

Pitfalls:
- `morpho-org/morpho-blue` main branch IS the deployed code (do not assume v2 changed the
  formulas) — but check constants: `LIQUIDATION_CURSOR = 0.3e18`, not 0.5e18.
- Healthy check: `floor(floor(coll*price/1e36) * lltv / 1e18) >= ceil(borrowShares *
  totalBorrowAssets / totalBorrowShares)` — a naive `coll/debt` HF without the LLTV factor
  flags nothing (coll/debt < 1 implies maxBorrow < borrowed, so hf<1 by the naive formula is
  unreachable while positions exist — the paper reviewer caught this).
- The 4th liquidate argument is `repaidShares` with `exactlyOneZero(seizedAssets,
  repaidShares)`: pass `seized = S, repaidShares = 0` to size by collateral, or
  `seized = 0, repaidShares = N` to size by debt. There is no "maxRepaid" cap argument on
  this version — cap principal by sizing `seized` off-chain.
- Flash loan `flashLoan(token, amount, data)` calls back `onMorphoFlashLoan(uint256,bytes)`
  (selector 0x31f57072) and pulls `amount` back after the callback: approve Morpho for
  exactly `amount` inside the callback.
- The price can move inside the block the liquidation happens in (here: Chainlink-style
  feed `0xa678cb16` updated mid-block): a tx replayed from before the block reverts
  "position is healthy". To reproduce a same-block liquidation on the fork, reset to
  block-1 and replay only the oracle update tx first.
