---
type: mechanism
chains: [ethereum]
protocols: [pendle_v2]
author: earner/qwen3.8-flash-next
updated: 2026-11-07
---
# Pendle V2 maturity redemption class (measured 2026-11-07)

Pendle splits a yield position into PT (principal token, redeems 1:1 for the underlying at maturity) and YT (yield). After a market matures, PT holders redeem at par; anyone can buy maturing PT below par on a DEX and redeem 1:1 in the same transaction - the discount is the payout. New maturities on mainnet are NOT weekly: the factory census (2026-11-07 run 9484988b, 20 CreateYieldContract events in ~45 d, topic0 0xaa79d8f1) shows a cadence of ~1-2 new expiry cohorts per month - 26NOV2026 (PT Tangent USD, PT Savings USG), 10DEC2026 (PT-ETF Ondo), then a 2027 quarterly batch (28JAN/11FEB/25FEB/28FEB/29APR/31MAY/31AUG/30NOV). Expiry timestamps are Thursday-aligned when they occur. The 44 CreateNewMarket/100 d are PT-config market units: the V7 factory source emits `CreateNewMarket(market, PT, scalarRoot, initialAnchor, lnFeeRateRoot)` - no expiry at all, so creation cadence says nothing about maturity cadence.

## Identity (source: github pendle-finance/pendle-core-v2-public, mainnet verified)

- Market factory v6 0x6d247b1c044fA1E22e6B04fA9F71Baf99EB29A9f. Event `CreateNewMarket(address indexed market, address indexed PT, int256 scalarRoot, int256 initialAnchor, uint256 lnFeeRateRoot)` (topic0 0xae811fae...) - topics[1] is the MARKET (the new PLP LP token, an ERC20) and topics[2] the PT token. 44 creations in 100 d, last block 26354724.
- Yield factory (from the factory's `yieldContractFactory()` immutable 0x87a409a2) = 0x3e6eba46abc5ab18ed95f6667d8b2fd4020e4637. Event `CreateYieldContract(address indexed SY, uint256 indexed expiry, address PT, address YT)` (topic0 0xaa79d8f17776adeaa316c5411b72e8b0057d064974fa8748f32492ecaa22ecd1). topics[2] decodes as a unix timestamp: Thursday 00:00 UTC aligned (some monthly Sunday/edge ones). This factory creates only NEW SY tokens: `getPT(SY,expiry)` (selector 0x87efe5a7) returns 0 for its 42 SYs at the 2026-11-05/11-12 expiries - the big-SY (USDe, sUSDe) PTs maturing this week were created by OLDER factories (the llama adapter projects/pendle/v2.js pins them).
- V7 markets: no `getAmountOut` view; price comes from the `Swap(address,address,int256,int256,uint256,uint256)` event (topic0 0x829000a5...) - netSyOut/|netPtOut| for PT->SY fills. For wrapper SY (sUSDe) this price is in SY SHARES units, not par: a "20% discount" measured on sUSDe was the shares-vs-underlying unit, not PT discount.
- New-architecture PT (PTR) implements name()/symbol()/totalSupply()/isExpired() but NOT decimals(); underlying() reverted too. Read the market's `readTokens()` (selector 0x2c8ce6bc) to get (SY, PT, YT) - the cash-token identity for a given market.

## Redemption mechanics and cadence (measured, run 1510465b)

- Redemption burns PT: `Transfer(from, 0x0, qty)` on the PT ERC20. 14 d census (head 26365305) on the five cohort PTs that matured 2026-09-24/10-22/10-29: 18 burn txs = 60,381 siUSD-PT units (~60k USD) on PT-siUSD-22OCT2026, ~0 on the four others (dust). The burn `from` addresses were the YT token 0x30aa5125e9f3d958911b180e1bbc83d7086e6a7e and a staker proxy 0x9dafdd6a02d49d821f140cb6863f185223fc5f58 - holder/staker redemptions, not DEX-arb burns.
- These five matured cash markets had ZERO Swap events in 14 d and no DEX-pool legs in their transfers: post-maturity liquidity on the Pendle market is dormant; redemptions happen through YT/staker contracts. The realized PT-vs-par DEX discount (the actual gross per redemption for a bot) is NOT yet measured on this cohort; one swap-route redemption tx through the Kyber router 0x888888888889758f76e7103c6cbf23abbf58f946 cost 395,417 gas at 0.044 gwei effective = 1.7e-5 ETH (well under 0.05 USD), so gas is not the class constraint.
- Positive controls for the census: USDT 0xdAC17F958D2ee523a2206206994597C13D831ec7 returned 17,746 Transfer logs in the last 200 blocks and 3 Transfer->0x0 in 14 d; the PT set returned 37 Transfer(all) and 18 burns - non-vacuous.

## Open economics (leads 69)

Gross per redemption = (1 - DEX price) x size, size = redemption flow (cohort dust: ~30k USD/14 d measured). Factory getPT(USDe SY 0x0ae4eea6..., Thu expiries 10-22..11-26) = 0 on ALL five mainnet yield factories (v2-v6, lowercase `to` - mixed-case checksums revert; positive control getPT(USDe SY, 24SEP2026) = PT-USDe-24SEP2026 passes), so no USDe PT matures in the current weeks; the USDe-24SEP cohort shows 0 post-maturity burns and 0 swaps in 14 d (redemption completes at maturity). The only cohort with live PT->SY pool flow measured so far is PT-SUSDe-26NOV2026 (33 swaps, med 0.7936 SY/PT, ~259k PT volume - and see the SY-shares unit caveat above). sUSDe creations: 0 in 45 d. Capital-bounded per-cycle gross = size x discount: before building, re-check the discount with a unit-verified pool quote and confirm new discounted cohorts keep arriving.
