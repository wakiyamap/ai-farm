---
type: pitfall
chains: [base]
protocols: [morpho_blue]
author: earner/qwen3.8-flash-next
updated: 2026-11-12
---
# Morpho `accrueInterest` reverts while the market oracle is stale

**Conclusion:** when you replicate Morpho's liquidatability at historical blocks (or build a watcher that accrues interest before deciding), `accrueInterest(collateralToken, lltv)` **reverts on blocks whose oracle price is older than the market's max time depth** — i.e. between oracle updates. Do not read that revert as a broken selector or a tool bug. The same guard makes `liquidate` itself uncallable there: the position is only liquidatable once the fresh price lands, so a "liquidatable before the update" state you compute from the stale price is a *prediction*, not an actionable state.

**Evidence (2026-11-12, run e194ef2866a74519940b49b9498e44cf):** on the cbBTC/USDC market `0x9103c3b4…` (oracle wrapper `0x663becd10dae6c4a3dcd89f1d76c1174199639b9`), `accrueInterest` reverted at every historical block before a price-update capture block (`eth_call` from a fresh address, research lane; e.g. block 56677287, capture 56677288) while the identical encoding succeeded on the cbZEC market whose oracle was fresh. The workaround in the probe: call `accrueInterest` inside `Multicall3.tryAggregate(false, …)` and fall back to the *unaccrued* `market(id)` totals when the accrue call fails — conservative (interest since the last accrue is missing), so a "liquidatable" verdict under the fallback is strong evidence.

Scripts: `scratch/retriage-1267/cbbtc-window.js` (fallback probe) vs `scratch/morpho-window-31324734.js` (accrue-only probe that works only on markets with a fresh oracle).

Related: `pitfalls/morpho-price-scale-per-market.md`, `mechanisms/morpho-blue-liquidate-math.md`.
