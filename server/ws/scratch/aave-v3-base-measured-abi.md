---
type: mechanism
chains: [base]
protocols: [aave_v3]
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
