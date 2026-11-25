---
type: mechanism
chains: [ethereum]
protocols: [compound_v2]
---

# Compound v2 accrueInterest pays the caller

The mainnet Compound v2 deployment (comptroller 0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b, 20 cToken markets, the 2024-migrated layout) pays the caller of `accrueInterest(uint256)` (selector 0xdb006a75) the interest accrued since the last accrue on that market. Anyone can call it; the payout is a real transfer: on cETH 0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5 the payout arrives as a CALL with value in native ETH (trace of tx 0x017b3d2e22b327463de410b4929290251180a02f8dbbacfa597a032c7f9030e0, block 26349231: cETH → recipient with 0x29b93611f05964b8 wei = 0.0299 ETH). The `newSupplyRateMantissa` parameter is validated on-chain against the market's interestRateModel (`getNextSupplyRate(utilization, accountCash, borrowBalanceStored, targetUtilization, kink)`), so a wrong/stale mantissa reverts and only gas is lost.

## Measured economics (7d census, blocks 26326000-26368000, 2026-11-08 run 22117954)

The protocol emits `AccrueDistributed(address cToken, address recipient, uint256 interestDelta, uint256 interestScalar)` on the comptroller (topic0 0x2caecd17d02f56fa897705dcc740da2d237c373f70686f4e0d9bd3bf0400ea7a): 1479 events in 7 days, of which only 158 paid anything > 0. The whole class pays **27.4 USD/day for all callers combined**, and 95 % of it (26.1 USD/day) is the **cETH market**; cAAVE pays 0.96 USD/day, the stablecoin and dust markets < 0.3 USD/day. `interestDelta` is in 1e18-scaled units for every market.

Payments concentrate in **gap events**: interest accumulates only between accrues; cETH accrues happen in ~67 blocks/7d (median gap 389 blocks, mean 590, max 3745 ≈ 12.5 h), and only the first call in a block captures the accumulated delta (of the 1085 repeat calls in the same (market, block), all paid 0). Big payments (≥ 0.5 USD) are 3.1 events/day with an average of 8.6 USD; 12 gaps ≥ 1000 blocks happened in 7 days. Because the gap grows over hours, a **poll keeper can precompute the trigger block** — this is not an oracle race.

Who takes the payouts: the big-payment winners are **scattered one-off EOAs** (each recipient of a ≥ 0.5 USD payment in the 7d window received exactly one), while the repeated callers (0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae 270 accrues/7d, 0x52ea46506b9cc5ef470c5bf89f17dc28bb35d85c 121/7d) mostly do zero-payment hygiene accrues (rate upkeep) and pay gas for it. The class is an open free-for-all, not incumbent-locked.

Gas: the winner's accrueInterest used 145154 gas (measured; keeper calls ~100-170k). Base fee measured 0.033 gwei at head 26368093 → cents per call today; the pool is comfortably positive only for cETH-sized triggers.

## Bot recipe (compound-accrue-ethereum)

Watch the last cETH AccrueDistributed block (cheap eth_getLogs with the comptroller address + topic0 + topic1=cETH filter); estimate delta ≈ elapsed_blocks × 1.95e-6 ETH/block (measured: 0.0818 ETH paid over 42000 blocks); when the estimate ≥ 0.002 ETH (≈ 4.5 USD) call an executor that accrues atomically and reverts unless its own balance gained ≥ minProfit → worst case is gas only. Prices ETH 2234.29 / AAVE 130.56 USD (coins.llama.fi, 2026-11-08).
