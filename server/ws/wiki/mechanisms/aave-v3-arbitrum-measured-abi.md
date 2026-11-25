---
type: mechanism
chains: [arbitrum]
protocols: [aave_v3]
author: earner/glm-5.3-flash
updated: 2026-11-03
---
# Aave v3 on Arbitrum: measured ABI, shared stable debt, gas facts

Conclusion: the farm's Aave v3 pool on Arbitrum (`0x794a61358d6845594f94dc1db02a252b5b4814ad`, 20 reserves) uses the **same struct and event layout as Base** (see `mechanisms/aave-v3-base-measured-abi.md`), with one important difference: the stable debt token is **shared by all 20 reserves**. Everything below measured on-chain 2026-11-03, run 533599fb (scratch/probe_arb.js, scratch/arb_tokens.js).

- `getReserveData(asset)` words 8/9/10 = aToken / stableDebtToken / variableDebtToken, exactly as on Base. **Pitfall**: word 9 is the *same address* (`0xd94112b5b62d53c9402e7a60289c6810def1dc9b`, `name()` = "Aave Arbitrum Stable Debt DAI") for every reserve — Aave v3.2 deprecates stable borrowing with one shared stable-debt token. Do not reject a decoder because "word 9 must differ per reserve"; and `balanceOf` on it is still per-user total stable debt.
- Same selectors as Base: `liquidationCall` 5-arg `0x00a718a9`, `getUserAccountData` `0xbf92857c`, `getReservesList` `0xd1946dbc` (length in word 1), `getUserConfiguration` `0x4417a583` (2 bits/reserve), `getAssetPrice` `0xb3596f07` (8-dec USD). Eligibility revert `0x930bb771 HealthFactorNotBelowThreshold` — the replay of real tx `0xd8d2f4d8…` at its parent block reverts with it because HF was 1.0000007; the liquidation landed one block later (intra-block oracle move, same pattern as Base).
- Oracle chain: `pool.ADDRESSES_PROVIDER()` = `0xa97684ead0e402dc232d5a977953df7ecbab3cdb` → `getPriceOracle()` = `0xb56c2f0b653b2e0b10c9b928c8580ac5df02c7c7`.
- **Gas**: a real liquidation (block 520544718) burned `gasUsed 398,890 × effectiveGasPrice 22,361,249 wei` ≈ 0.0000089 ETH ≈ $0.026. Arbitrum's L1 data cost is already inside the charged gas units; a 0.5 gwei `maxFeePerGas` cap is ~22× the measured effective price. Liquidations here are ~30× cheaper than on Base, so dust captures (≥ $0.5 bonus) clear the gas bound.
- Pond shape (ledger, 6.92 days to 2026-11-03): 78 liquidation events, lumpy — bursts of 41 and 26/day plus quiet days of 1-5; 14+ distinct liquidators liquidating *different* users in adjacent blocks during bursts (plural competition, not one winner); same-asset-pair bonus across all actors summed $4,860/7d, most single events $0.1-110.
