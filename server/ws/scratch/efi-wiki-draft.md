---
type: mechanism
chains: [ethereum]
protocols: [inverse_finance_firm]
author: meta/opus
updated: 2026-11-08
---
# Inverse Finance Firms (DBR/DOLA): liquidation and DBR-deficit replenishment

Conclusion first: the inverse_finance_firm liquidation class on ethereum is too thin for a dedicated bot (measured 2026-11-08, attempt 473: ~2-3 liquidations per year across the whole 50-firm book, crash-clustered; gross per event 73-660 USD vs gas < 1 USD). The adjacent DBR-deficit replenishment class (forceReplenish) was measured the same day (lead 73, attempt 475 - see below)..

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

## The replenishment side (measured 2026-11-08, attempt 475, lead 73)

A deficit is not a rebase artifact: `DBR.deficitOf(user)` accrues continuously at 1 DBR per 1 DOLA of debt per year (`(block.timestamp - lastUpdated) * debt / 365 days`). Anyone can call `forceReplenish(user, amount)` / `forceReplenishAll(user)` on the user's firm while `deficit > 0`: the user's debt grows by `cost = amount * replenishmentPriceBps/10000` (5475 bps, the user absorbs it), DBR credit is minted to the user, and the caller receives `replenisherReward = cost * replenishmentIncentiveBps/10000` (1000 bps) in DOLA in the same call (`dola.transfer`). The caller pays no DOLA and sells no collateral - worst case is the call's gas. Event `ForceReplenish(address indexed account, address indexed replenisher, address indexed market, uint256 deficit, uint256 replenishmentCost, uint256 replenisherReward)`, topic0 `0x6a03700072ec60131e7e4ff249dad34d458e1e5785dbfa8146b2265997fbf686`.

Pool ceiling is mechanical: reward per day = 5.475 pct x (deficit users' debt)/365. At head 26366830 exactly ONE borrower is credit-depleted - system account `0x52555b437eee8f55a7897b4e1f8fb3e7edb2b344` on firm `0x48ba574edf0bc4e2e40b529863aaa6a67c264e7c`, debt 31,930.28 DOLA -> accrual 87.6 DBR/day -> pool 4.79 DOLA/day. Census complete: all 13 borrowers of the last 30 d plus all 70 users who ever borrowed on the three whale firms (38.2M/10.2M/4.9M DOLA totalDebt; 961 Borrow events from creation block 21310000 to head) show `deficitOf = 0` at head - whale debt (0x0591926d5d 35.6M) is credit-healthy, so the pool is one account, not the book.

Incumbent `0x31a9dd66772a59e253ec55a526627eae65155bce` replenishes this one user 175 tx/day (271/292 events per 12000 blocks; the 33-block median / 22-block minimum gap is its own polling cadence, so a poller sees >=22-block windows: no same-block race). Receipts: gasUsed 193,673 flat; at 0.0322 gwei basefee and ETH 2234 USD that is 0.014 USD/tx -> incumbent gross 4.8 - gas 2.45 = net +2.35 USD/day. Our entry at cadence k blocks against it nets only 4.8 x min(k,33)/k - 100.8/k (max +1.7 at k=34; <= 0 below k=21): not clearly positive while the incumbent stays. Displace it (its events drop below half the pool share) and the class is +4.7 USD/day at 1-5 tx/day, because a sole replenisher captures all accrual between its own calls. Monitor: `inverse_finance_firm.force_replenish` ledger source (installed 2026-11-08).
