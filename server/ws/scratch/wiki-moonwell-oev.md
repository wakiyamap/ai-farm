---
type: mechanism
chains: [base]
protocols: [moonwell]
---
# Moonwell Base liquidations: plain mToken LiquidateBorrow, OEV wrapper unused

**Conclusion:** Moonwell core-market liquidation is a Compound-v2 mToken event: the loan
mToken emits `LiquidateBorrow(liquidator, borrower, repayAmount, mTokenCollateral,
seizeTokens)` with everything in data. On Base this class is alive (~104 events/day on
just two loan markets, 44 competing liquidators) but **dust-dominated** (median repay
0.06 USDC). Moonwell's per-collateral `ChainlinkOEVWrapper` contracts delay the fresh
Chainlink price by `maxRoundDelay`=10 s and pay the caller `liquidatorFeeBps`=40 % of
the liquidation profit through `updatePriceEarlyAndLiquidate()`, emitting
`PriceUpdatedEarlyAndLiquidated(borrower, repayAmount, mTokenCollateral, mTokenLoan,
protocolFee, liquidatorFee)` — but the Base WETH-core wrapper logged **zero** of those
in the measured 7-day window: nobody on Base uses the OEV route, so the wrapper is not
where the liquidations are. After the 10 s delay the fresh price is public anyway
(docs "OEV Liquidator Bot": the window is competitive, multiple bots target one update).

## What is on-chain (measured 2026-11-05 through the relay)

- Moonwell docs list the Base "Comptroller" proxy
  `0xfbb21d0380bee3312b33c4353c8936a0f13ef26c` (Unit-proxy: implementation in slot 0,
  `eth_getStorageAt` slot `0x0` → mixin `0x8b621804a7637b781e2bbd58e256a591f2df7d51`).
  It is live and emits `MarketEntered(address,address)`
  (topic `0x3ab23ab0…`, 675 hits in a 40k-block 2025-08 window, 6 in the last 40k
  blocks), governance topics, and **no** `Liquidate(address,address,uint256,uint256)`
  event (`0xf3fa0ea…`) in any scanned window from block 10 M to head — the docs event
  table lists no Liquidate either. Cadence scans must therefore use the wrapper event,
  not a comptroller Liquidate event.
- Core markets are not dormant: `totalBorrows()` returns 7,532,789.9881 USDC
  (mUSDC `0xedc817a28e8b93b03976fbd4a3ddbc9f7d176c22`), 1410.77 WETH
  (mWETH `0x628ff693426583d9a7fb391e54366292f509d457`), 58.65 cbBTC
  (mcbBTC `0xf877acafa28c19b96727966690b2f44d35ad5976`), 13,031.59 DAI
  (mDAI `0x73b06d8d18de422e269645eace15400de7462417`). eth_call at head 53542238.
- WETH-collateral core wrapper `0xeb083d234ec636a10325ea42bcbbe09aa56d1547`
  (docs "Core Markets - Deployed Contracts", Base). Docs list one wrapper per
  collateral; the docs page names only WETH for core markets on Base.

## Cadence (measured 2026-11-05, blocks 52246238–53542238 ≈ 7.1 days)

The liquidation event itself is on the **loan mToken**, not the comptroller:
`LiquidateBorrow(address,address,uint256,address,uint256)` topic
`0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` — all five
fields (liquidator, borrower, repayAmount, mTokenCollateral, seizeTokens) in data,
no indexed topics. The docs event tables confirm this signature; the Compound-v2
`Liquidate` topic is absent from every Moonwell contract scanned.

- mUSDC `0xedc817a28e8b93b03976fbd4a3ddbc9f7d176c22`: **679 events / 7.1 d ≈ 95/day**;
  repay sum 52,840.45 USDC, mean 77.82, median 0.0604 (dust), 13 events ≥1 USDC,
  none ≥100 USDC in the window, max 37,065.97 (whale). 549/679 seized mWETH collateral.
- mWETH `0x628ff693426583d9a7fb391e54366292f509d457`: **60 events / 7.1 d ≈ 8.4/day**;
  repay sum 0.7038 WETH (median 0.0001, max 0.5646 WETH ≈ 1,360 USD at $2400/ETH).
- OEV wrapper `0xeb083d234ec636a10325ea42bcbbe09aa56d1547` (docs, WETH core):
  **0** `PriceUpdatedEarlyAndLiquidated` in the same window — the 10 s OEV route is
  unused; all measured liquidations go plain `liquidateBorrow`.
- 44 distinct liquidators (top two did 389 and 136 of the 739 events), 562 distinct
  borrowers, 116 borrowers liquidated more than once.
- Ledger source `moonwell_core.liquidate_borrow` installed for these two markets.

## Fit for the farm

- Profit per event is the liquidation discount on `repayAmount` minus gas; measured
  repay flow is dust-dominated so per-event gross is usually cents, and whale events
  (one 37,065.97 USDC repay in 7 days) carry most of the value. 44 liquidators share
  ~104 events/day — a newcomer pays full gas per event unless it batches like the top
  liquidator.
- The farm already farms the same Morpho pond: Moonwell's isolated "Morpho Markets"
  liquidate through Morpho Blue `0xbbbbbbbb…ffcb` and are already in the ledger's
  morpho_blue class; the Moonwell core-market OEV class is the part the ledger misses.
- Principle 2 check: the OEV window is a ~10 s race *while the price is delayed*;
  after the delay any poller competes at the fresh price. A poll-based bot can take
  the post-window liquidations; winning the window itself needs speed we do not have.
