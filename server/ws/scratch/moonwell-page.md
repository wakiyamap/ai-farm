---
type: mechanism
chains: [base]
protocols: [moonwell]
author: earner/qwen3.8-flash-next
updated: 2026-11-05
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

## Window sampling (measured 2026-11-05, attempt 192, script scratch/mw-window-batch.py, output scratch/mw-window-batch.json)

`getAccountLiquidity(holder)` on comptroller `0xfbb21d03…` probed at historical blockTags
(relay `blockTag X` = state **before** block X is applied; return word1 wraps negative =
liquidatable) for every one of the 26 ledger events with `repayAmount >= 10 USD` in 7.1 days:

- **15/26 were already liquidatable >= 8 blocks before capture**; 12 are bracketed at >= 32
  blocks and 3 were liquidatable **32,768 blocks (≈ 18 h) before capture** without finding the
  crossing (blocks 53265174, 53268172, 53489444 — these accounts sat liquidatable for a day+).
  A poll-based bot does not race for these: the window outlasts any poll interval.
- **11/26 were healthy 2 blocks before capture** — crossing happens inside the capture block
  (interest-bleed grind holders `0x689584e4` ×4, `0xbf65b647` ×3, `0x3ac21455` ×2, re-liquidated
  as they re-cross; whale self-liquidations sit here). Same-block race class; not the bot's target.
- Approx repay sum: catchable-window class ≈ $41.5k vs same-block ≈ $0.8k per 7.1 d; gross
  liquidator edge ≈ 11.11 % × repay ≈ $650/day for the catchable class at full capture
  (44 liquidators share events, so realized share is lower).
- Moonwell core collateral markets do **not** answer the Compound-v2 `underlying()` selector
  `0x6d342007` (eth_call reverts on all sampled markets; names via `name()`: Moonwell USDC
  `0x703843c3`, Moonwell WETH `0xdc7810b4`, Moonwell cbETH `0x3bf93770`, Moonwell EURC
  `0xb682c840`, Moonwell Virtual `0xde8df9d9`). Resolve the per-market underlying getter before
  hard-coding swap routes. mUSDC-collateral captures (e.g. block `53489444`, 76.26 USDC repay)
  need no swap at all: seize mUSDC, redeem, repay USDC.
- The price feeder `0xec942be8…` emits **no logs** (eth_getLogs 40k blocks → 0 events): watch
  holders directly by polling; feeder-watch is only needed for the same-block whale class.

## Cashless markets and the seize cap (measured 2026-11-05 run eb603abb, attempts 198/199, scratch/mw-whale/)

Atomic repay-redeem-swap executors fail on this class for two measured reasons:

- **Deprecated core markets are cashless.** mToken `getCash()` (selector `0x3b1d21a2`,
  returns cash in 1e18 scale) at the measured events: wrapper-mcbETH `0x3bf93770`
  154486718 wei (≈1.5e-10 underlying), mEURC `0xb682c840` 14163 wei, mUSDC `0xedc817a2`
  103028 wei — while raw-cbETH `0xde8df9d9` ≈ 8.8e22 (≈88k USD) and mADA `0xdc7810b4`
  ≈ 95k USD. `redeemUnderlying` is capped by market cash, so redeeming seized collateral
  on the cashless markets returns ~0 and a flash-loan executor loses its repay.
- **The mToken caps the seize to half the holder's collateral balance**
  (`LIQUIDATE_SEIZE_TOO_MUCH` revert): the liquidatable-class holders measured here hold
  near-zero collateral (`balanceOfUnderlying(holder)` on event 53517752 = 58203 wei),
  so the maximum atomic repay is ~0.02 USD and the atomic profit is dust. The whales
  repay up to `repayAmount` (e.g. 8303 USD borrow-amount parameters), seize the mToken
  shares and realize them later (or at market close) — not through an atomic redeem.
- Probe outcomes at the 26 whale events (repay ≥ 10 USD) of the last 7.1 d and at the
  14 older raw-cbETH-market events (scratch/mw-whale-cands.json): the events liquidatable
  before capture are on cashless or dust collateral; every event on a cashed collateral
  market was healthy at block−1 (same-block capture) and its account was **healthy again
  after capture** — the whale repayment heals it, so there is no follow-up liquidation
  window on the same block. `borrowBalanceCurrent` is in **underlying 1e6 units** (mUSDC),
  not the 1e18-USD scale of `getAccountLiquidity` shortfall.

## Liquidatability windows: chronic accounts are multi-hour, fresh crossings are same-block (measured 2026-11-06, run 6c25eb5e)

**Conclusion:** the class is mixed. A chronic-underwater holder stays liquidatable for
hours before anyone captures it — poll-catchable with no fast infrastructure. A fresh
small default crosses liquidatable **inside** the block that captures it (0-block window,
same-block race class).

Probe = `eth_call` comptroller `0xfbb21d0380bee3312b33c4353c8936a0f13ef26c`
`getAccountLiquidity(address)` (selector `0x5ec88c79`, word 3 = shortfall in 1e18-USD)
on the local Base fork after `fork reset base <block>`; script `scratch/mw-window/probe.sh`.

- Chronic holder `0x21df358f`: shortfall 84.17–84.59 USD **flat from at least 20,000
  blocks (≈11 h) before its capture** at block 53786333
  (tx `0x7ae200e3302dd19f1af51faeb7e2b3b5635c461ca97464c2a5c40fe9a58c4f7d`), still > 0 at
  block−1 where the proof11 executor succeeded. Chronic accounts get captured
  repeatedly: `0x73ebc729` was seized 4× in 3,400 blocks (blocks 53516624–53519985).
- Fresh default `0x11dbfcf6` (repay 43.83 USDC, block 53799551
  tx `0xf34707e5f5b202d7be2629f77de6513e15a272bd112ec0449b5aaeb86af91421`): shortfall 0
  at every probe from block−10000 to block−1 — it crossed eligibility inside the capture
  block. Same-block capture per `wiki decisions` (no-latency-race, 2026-11-06).

So a 15 s poll bot can win a chronic holder in time; it will systematically miss the
fresh-crossing captures, which belong to the block-rate keepers.
