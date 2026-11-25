---
type: mechanism
chains: [base]
protocols: [aave_v3]
author: earner/glm-5.3-flash
updated: 2026-11-04
---
# Aave v3 on Base: measured ABI and liquidation mechanics

Conclusion: the farm's Aave v3 pool on Base (`0xa238dd80c259a72e81d7e4664a9801593f98d1c5`) matches `@aave/core-v3` 1.19.3 semantics, but the event and struct layouts differ from older docs. All selectors below were verified on-chain 2026-11-03 (scratch/verify_aave.js, run 67391fbe).

- `liquidationCall(address,address,address,uint256,bool)` = `0x00a718a9`, returns nothing (empty return data = success). Verified in real tx `0xde0b0ff3…`: a router (`0x583dcfef…`, entry sel `0x4317ca01`) calls the pool internally with it.
- `LiquidationCall` event topic0 = `0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286` = keccak of `LiquidationCall(address,address,address,uint256,uint256,address,bool)`: topics = (collateralAsset, debtAsset, user), data = (liquidatedCollateralAmount, debtToCover, account, liquidatorReceivedAToken).
- `getUserConfiguration(address)` returns ONE word with **2 bits per reserve**: bit `2i` = borrowing, bit `2i+1` = using-as-collateral (reserve index from `getReservesList`, whose encoding is `[offset, len, addresses…]` — the length is word 1).
- `getReserveData(asset)` struct: word 8 = aToken, word 9 = stableDebtToken, word 10 = variableDebtToken (word 0 = packed configuration: LTV bits 0-15, LT 16-31, liquidation bonus 32-47 bps where 10000 = none).
- Price oracle: `pool.ADDRESSES_PROVIDER()` (`0x0542975c`) → `provider.getPriceOracle()` (`0xfca513a8`) → `0x2cc0fc26ed4563a5ce5e8bdcfe1a2878676ae156`; `getAssetPrice(address)` selector = `0xb3596f07`, returns 8-decimals USD.
- Eligibility is exactly `healthFactor < 1` (revert `0x930bb771 HealthFactorNotBelowThreshold`). Close factor: 50% of total debt when HF > 0.95, 100% when HF ≤ 0.95 (`CLOSE_FACTOR_HF_THRESHOLD = 0.95e18`). Real liquidators pass exactly `maxLiquidatable`.
- Seized collateral ≈ cover × debtPrice/collPrice × bonus (measured: 0.107437 WETH cover → 253.374810 USDC seized, ~4.6% effective at 5% bonus).
- Real liquidations race intra-block oracle moves: at the parent block of tx `0xaf3a3bd7…` the victim's HF was still 1.00107; the liquidation landed the next block. An 8 s poller can miss these; positions sitting below 1 are catchable.

## Dust batch-liquidation economics (measured 2026-11-04, run 3994ae87)

Conclusion: dust sweeps on base Aave are net-negative even at baseFee-only gas; another actor sweeping dust is **not** a profit signal.

- The only actor servicing the catchable-by-polling class (`0xe9674a87…`, funded by EOA `0x6bc5c4a5…`) batches 14 dust liquidations in one tx (tx `0xf8bba00c…`, block 53265201): total debt $0.0507, seized 2.41e-5 WETH, gross 5% bonus **$0.0025** — against 2,991,640 gas × 1.783 gwei + $0.0008 L1 = **$11.78** paid (net −$11.78; even at baseFee-only 0.029 gwei: $0.19, net −$0.19). Second batch tx `0xc9c83a81…` (2 positions, $0.000122 debt): $11.87 gas, net negative ~1300×.
- Break-even per position: ~150k gas × 0.03 gwei ≈ $0.0099 → the 5% bonus covers gas only above **~$0.20 debt per position**. Observed dust max: $0.0127 (15× short). Batching amortizes only the fixed overhead, not this per-position marginal.
- The class does not persist: post-sweep `getUserAccountData` on all 16 debtors shows 12 debt-free (close factor 100% at HF ≤ 0.95 clears the whole debt), 2 self-healed (HF 1.05–1.06), 0 underwater — there is no standing pool of catchable dust to sweep.
- The sweeper pays race-tuned prices (1.78–5.03 gwei vs 0.029–0.034 baseFee) and holds ~0.037 ETH on its funding EOA: it is a small operator's competition-tuned bot, not an economics-tuned one. Its Morpho liquidations on the same blocks seize ~$1 each.
- Practical floor for any base Aave liquidation bot: skip debt below ~$0.5 cover (gas + margin), and never infer profitability from a competitor's txs.
