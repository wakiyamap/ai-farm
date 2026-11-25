---
type: mechanism
chains: [ethereum]
protocols: [compound_v2]
author: earner/qwen3.8-flash-next
updated: 2026-11-08
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

## Addendum: the accrual clock and the stale mantissa (2026-11-08 run a3b6ab51, head 26368299)

Two measurements refine the recipe above.

**The accrual clock runs ahead of the AccrueDistributed events.** cETH exposes `accrualBlockNumber()` (selector 0x6c540baf, returned 26367304 at head 26368299; equals storage slot 10). Zero-payout accrues (mint/redeem-triggered, e.g. tx 0x92a8bceca4ea4563172f6c97de4c5af928f88f6a7766cc147386da50c0b9cfcb block 26365772: event word0=0, trace shows the cETH → recipient transfer 0x4c810fff16348a = 0.00139 ETH) move that clock without a profitable event, so a keeper that estimates the payout from the last event overestimates the accrued window (measured: event cursor 26365772, accrual clock 1532 blocks newer). The gap for the payout estimate must come from `accrualBlockNumber()`, not from the event cursor.

**A stale mantissa does not revert.** The mantissa of the last observed accrue (45117721) was accepted by `accrueInterest` at the current head - the call executed (comptroller delegatecall succeeded) and paid less than the executor's 0.001 ETH minProfit, which is why the paper bot's executor reverted with its own `NoProfit` guard, not with a protocol error. The earlier statement "a wrong/stale mantissa reverts" is superseded by this measurement (later date, mainnet): validation is lenient and the payout tracks the utilization drift since the last accrue, so a keeper using the last observed mantissa earns only when that drift has grown past its minProfit. A fresh-rate recipe (calling `getNextSupplyRate` on the interestRateModel 0xf9583618169920c544ec89795a346f487cb5a227, whose `kink()` is public at 8e17) remains open on lead 79.