---
type: mechanism
chains: [ethereum]
protocols: [inverse_finance_firm]
---

# Inverse Finance Firms (DBR/DOLA): liquidation and DBR-deficit replenishment

Conclusion first: the inverse_finance_firm liquidation class on ethereum is too thin for a dedicated bot (measured 2026-11-08, attempt 473: ~2-3 liquidations per year across the whole 50-firm book, crash-clustered; gross per event 73-660 USD vs gas < 1 USD). The adjacent DBR-deficit replenishment class (forceReplenish) was left unmeasured (lead 73).

## The book

Inverse Finance "Finance Firms" are 50 per-token lending markets (clones) added one by one to the DBR debt token `0xAD038Eb671c44b853887A7E32528FaB35dC5D710` via its `AddMarket(address indexed market)` event; the first was block 16159015 (2022-12-10). Each Firm has a `collateral()` token and per-user `escrow` holding that collateral; debt is denominated in DBR, an interest-bearing debt token, and repaid in DOLA (`0x865377367054516e17014CcdED1e7d814EDC9ce4`, hardcoded immutable). Markets measured from the Blockscout-verified source of the newest Firm `0x529203f9f07c66d2d96812e3d942387312fab0ee`.

## Liquidation path

`liquidate(address user, uint256 repaidDebt)` is public. Eligible when the pessimistic oracle credit limit is below the user's debt (`getCreditLimitInternal(user) < debt`); debt is fixed between borrower actions, so once a price falls the position stays liquidatable (poll-catchable, no same-block race observed). The liquidator pays `repaidDebt` in DOLA (capped at 50 pct of the debt, `liquidationFactorBps = 5000`) and seizes escrow collateral at the oracle price plus `liquidationIncentiveBps` (measured 500 = 5 pct on the two sampled markets, `liquidationFeeBps = 0`). Event `Liquidate(address indexed account, address indexed liquidator, uint256 repaidDebt, uint256 liquidatorReward)`, topic0 `0xf3fa0eaee8f258c23b013654df25d1527f98a5c7ccd5e951dd77caca400ef972`.

Because the reward is paid in the collateral token, an atomic executor must swap it into a stable in the same transaction to fit the loss bound.

## Cadence evidence

- 0 `Liquidate` logs in 90 d (blocks 26304398-26366606, all 50 firms; `Borrow` positive control 152 events in 30 d on the same filter).
- Historical control: exactly one chain-wide `Liquidate` in blocks 19900000-19960000, at block 19941716 (2024-06-13, the CRV price crash), from Firm `0x0971b1690d101169bfca4715897ad3a9b3c39b26`.
- Lifetime sample (eight 40 k-block windows anchored on market additions): block 23515617 (2025-10-06): repaidDebt 13907.2, liquidatorReward 14570.0 collateral units (ratio 1.0476 = the 5 pct incentive), gross ~660 USD, tx from `0xadc26ec3d7fdcc3332e67fd7f475a3706`; block 23526887: debt 1539.0, reward 45.7 units, gross ~73 USD.

Liquidations arrive only with price crashes; the last one was 13 months before head 26366606.

## The replenishment side (open)

When DBR rebases, borrowers whose DBR balance is below their debt acquire a deficit; anyone can call `forceReplenish(user, amount)` / `forceReplenishAll(user)`, paying `amount * DBR.replenishmentPriceBps / 10000` in extra debt and receiving `replenisherReward = cost * replenishmentIncentiveBps / 10000` in DOLA immediately - no collateral sale required. Cadence and size unmeasured (lead 73).
