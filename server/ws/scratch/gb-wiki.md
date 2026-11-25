---
type: mechanism
chains: [ethereum]
protocols: [gearbox-v3]
---

# Gearbox V3 credit-account liquidation

Conclusion: on Gearbox V3 (ethereum) a liquidation is one public call to the per-CreditManager `CreditFacadeV3`, the debt is repaid **from the liquidated account's own collateral**, and the liquidator keeps the underlying surplus in the same transaction. No liquidator principal and no flash loan are needed; the worst case is the call's gas.

## Flow (verified source, Blockscout `CreditManagerV3` + `CreditFacadeV3`)

1. Anyone may call `CreditFacadeV3.liquidateCreditAccount(creditAccount, to, calls, lossPolicyData)`. It is guarded only by `whenNotPausedOrEmergency` and by `_revertIfNotLiquidatable(creditAccount)`: the facade recomputes `calcDebtAndCollateral` inside the tx, so health must fail **at the moment of the call** (no registry, no first-participation gate).
2. The facade then calls `CreditManagerV3.liquidateCreditAccount(creditAccount, collateralDebtData, to, isExpired)` (`creditFacadeOnly`). The manager transfers the underlying `amountToPool` from the credit account to its pool (repaying the debt with the account's own collateral), and transfers the remaining underlying surplus to `to` — the address the liquidator passed. The liquidator's calldata `calls` (multicall) may include `onDemandPriceUpdates` and swaps run through the credit account; `calls=[]` is valid for accounts whose surplus is already underlying.
3. The facade emits `LiquidateCreditAccount(address indexed creditAccount, address indexed liquidator, address to, uint256 remainingFunds)` (topic0 `0x7dfecd8419723a9d3954585a30c2a270165d70aafa146c11c1e1b88ae1439064`). One CreditManager = one facade (a singleton per manager, not per chain).

## Premium and profit (measured 2026-11-07, run 09d1ec19)

Premium is `liquidationPremium` per manager, internal; measured from receipts as `surplus / (amountToPool + surplus)` on five healthy-account events: 3.75%, 4.01%, 4.31%, 4.39%, 4.60% — i.e. ≈4% of account value, and it scales with the account size, which is why gross ranges from 0.0044 WETH (~15 USD, tx 0x13818a90...) to 88.94 wstETH (~130k USD gross, tx 0x2231287c...). Expired-account liquidations use `liquidationDiscountExpired` and can pay out far more than 4% (tx 0x2231287c... captured 52% of account value).

Cadence and windows (8 events, 26 days, topic0 scan on the three active facades): five accounts became liquidatable only in the block before capture (same-block race, out per the 2026-11-06 human decision); three had poll-catchable windows of 34, 4,328 and 10,398 blocks (`isLiquidatable(account,10000)` bisected on historic blocks through the relay). Gas used by the six distinct liquidators: 728k–1.69M per tx (they bundle swaps and price updates in the liquidation tx itself); basefee 0.047 gwei at head 26,359,977 → ≈0.06 ETH per liquidation.

## Pitfalls

- `remainingFunds` in the event data is the value left **on the account**, not what the liquidator received; measure the liquidator's profit from the ERC20 transfer to the liquidator inside the liquidation call (it is emitted *before* the facade event).
- The underlying is per-credit-manager (`CreditManagerV3.underlying()`, immutable): pools are WETH, wstETH, USDS, USDC, WBTC books, so surplus arrives in that manager's underlying token.
- Small-debt accounts exist (~$15 gross): a size floor is part of the route, not an optimization.
