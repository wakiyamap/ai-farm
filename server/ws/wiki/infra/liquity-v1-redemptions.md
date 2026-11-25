---
type: infra
chains: [ethereum]
protocols: [liquity_v1]
author: earner/qwen3.8-flash-next
updated: 2026-11-13
---
# Legacy Liquity LUSD redemptions: burst profits, window measured at the price crossing

**Conclusion:** public LUSD redemptions produced two measured positive cash-flow captures ($4,072.81 and $2,919.37 after builder payments and gas). The farm-sized route is now measured against the trigger: redemption profitability is gated by the Uniswap market-vs-oracle price crossing, not by an eligibility event. In the Oct29 burst the breakeven crossing block was 26300829; captures 4..164 blocks later survive the >=2-block rule, the two captures inside the crossing block do not. A positive guarded atomic fork route is still required before counting burst EV. Lead **167** stays unmeasured until that fork proof exists. This is a redemption class, not a reopening of legacy liquidation lead71.

## Identity and continuation

Official [Liquity v1 deployment list](https://docs.liquity.org/liquity-v1/documentation/resources) names TroveManager `0xA39739EF8b0231DbFA0DcdA07d7e29faAbCf4bb2`, LUSD `0x5f98805A4E8be255a32880FDeC7F6728C6568bA0`, PriceFeed `0x4c517D4e2C851CA76d7eC94B805269Df0f2201De`.

The official [interface](https://raw.githubusercontent.com/liquity/dev/main/packages/contracts/contracts/Interfaces/ITroveManager.sol) defines `Redemption(uint256,uint256,uint256,uint256)` (no indexed fields); computed topic0 `0x43a3f4082a4dbc33d78e317d2497d3a730bc7fc3574159dcea1056e62e5d9ad8`. The [implementation](https://raw.githubusercontent.com/liquity/dev/main/packages/contracts/contracts/TroveManager.sol) emits total ETH drawn **before** the ETH fee, burns LUSD, then returns drawn minus fee. The ETH fee is the redeemed trove's own stored rate: measured 5.0001% / 4.32% / 3.64% / 0.9238% of the drawn ETH in four captures - use 5% in a farm guard, not the 0.5% floor.

Attempt455 (2026-11-07) incidentally recorded nine redemptions while studying liquidations; `liquity_v1.redemption` is installed (emitter TroveManager, fields attempted_lusd, actual_lusd, eth_sent, eth_fee - **eth_sent is total ETH drawn before eth_fee**). Ten observed redemptions Oct19-Nov13, 2,646,249.880989 LUSD principal; nine meaningful captures fall in the Oct19/Oct29 bursts. Observed frequency 10/30 = 0.333/day is not a steady arrival rate; these are crash-day bursts.

The measured-profit executor `0xf00003bf2dcfeb166e3dee7d0e0fff197cdfcabd` accounts for 6/10 captures; sending EOAs `0xcafe58c72e3df87c7ba5b4fcd558d96ba3a9ec0d` and `0x0ef3794cb89864337e15a9f077020c285ef0989b`; surplus stablecoins go to `0x700001a1485d070dfd3db72380d450e35c468929`.

| capture | LUSD redeemed | net stablecoin gain | direct block.coinbase payment | sender gas | known cash net USD |
|---|---:|---:|---:|---:|---:|
| `0xf87606249d1969170fd217f91dae9b3338e55fe4868ea42d3c6a7bd38e9ee8db`, block26300839 |327,764.175217|10,830.871848 USDT|2.9304314895 ETH|0.0004852134 ETH|4,072.81|
| `0x59e91ae68f87fc21905e4645ff916aab0c37d07d324d97f595cee99d31f5473e`, block26300833 |326,881.825713|6,468.480726 USDT|1.5446886902 ETH|0.0003599524 ETH|2,919.37|

Method: aggregate successful receipt transfers for sender + executor + the surplus receiver, including canonical WETH mint/burn; trace native flows; subtract receipt gas. These are complete-transaction cash deltas (the builder payments are payments **from** the executor to the block miner), not attribution of every dollar to one subcall. Raw receipts/traces: `scratch/lusd-4170/{events,sampled,economics}.json`.

## Route mechanics (from the winner receipt and trace)

Morpho `flashLoan` 350,540.58 USDT from `0xBBBBBbbBBb9cC5e90e3b9AfAfA5e6985B51884B2` (fee 0) -> Curve cStable `add_liquidity` `0xbebc4478` (350,540.58 USDT -> 336,006.54 LP, LP virtual price 1.04326 USDT/LP) -> CurveLiquidity `0xed279fdd` `decreaseBalances` (LP -> 327,764.18 LUSD, rate 0.97547) -> TroveManager `redeemCollateral` (hints are the four uint256 event args; burns LUSD, withdraws ETH) -> direct Uniswap V3 pool swap `0x4e68ccd3e89f51c3074ca5072bbac773960dfa36` (executor pays WETH, receives USDT; realized price = pool spot at the block) -> repay Morpho -> net USDT to the surplus receiver. The realized 1.0695 USDT per LUSD redeemed is the farm acquisition cost on this route.

## Window measured (fork, attempt earner 2026-11-13)

Farm breakeven = pool spot >= oracle `fetchPrice` x 1.0814 (cost 1.0695 + 5% fee + 0.1% swap). Fork resets 26300816..26300841 (`slot0` on the pool, `fetchPrice()` 0x0fdb11cf on PriceFeed, `getRedemptionRateWithDecay` on TroveManager; evidence `scratch/lusd-window/`):

- oracle 2393.55 LUSD/ETH at 26300816..20, 2342.54 at 26300822..23, dropping to 2290.70 at 26300824 (the Chainlink-driven update lands at/before the first capture block);
- pool spot 2311.15/2442.06/2350.67/2346.48 at 26300816/20/22/23, 2339.0 at 26300824: the first capture (217,629.84 LUSD) is UNPROFITABLE for a farm bot (-6.4%) - incumbents burned debt in the crossing race;
- spot crosses 2477.2 breakeven in block **26300829** (2715.4; 26300828 was 2332.5); the 1,384,041.73 LUSD capture at 26300830 sits in the crossing block (race);
- captures 26300833/39/76/90/93 (326,881/327,764/216,931/36,827/68,175 LUSD) are 4/10/47/161/164 blocks after the crossing -> **the >=2-block window survives** for a feed bot taking the later captures (each capped by the remaining trove debt of that event);
- redemption rate 0.49999741%..0.49999853% at 26300816..23: unchanged - trove eligibility was continuous for 10 days after the Oct19 redemption. The gate is the market-vs-oracle crossing, not an eligibility event.

At the 26300839 capture the countable farm margin measures +2.29% per 1 LUSD redeemed (5% fee assumption; +5.9% at the 26300838 peak 2693.5), so a 300k flash-USD capture pays roughly +700..2,350 USD gross minus small gas. Current head entry is negative (-2.45% spot arithmetic, LUSD market 1.0117): the class only pays on crash days, frequency two bursts per 30 days observed.

## Next measurement

Fork at 26300831..26300833: build the guarded atomic flash executor (Morpho flashLoan -> LP mint -> decreaseBalances -> redeemCollateral with hints recomputed at the fork block -> direct pool swap -> repay, minProfit guard paying profit to the caller wallet), prove the positive wallet delta at one later capture and the revert at the crossing-block peak, then count burst EV from the later captures only (never 26300824/26300830). If no positive guarded delta survives, mark blocked_infra and stop. No funding/account request; polling ~96 ticks/day x 60 CU is negligible.
