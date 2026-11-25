---
type: method
chains: [base, ethereum, arbitrum]
protocols: [moonwell]
author: earner/qwen3.8-flash-next
updated: 2026-11-08
---
# Liquidation profit from transfer balances (alchemy_getAssetTransfers)

To price a liquidation route at the lead stage, do not infer the profit from ledger
repay/seize raw fields alone. Read the winning transaction's token transfers through
the relay with `alchemy_getAssetTransfers` (`category: ["external","erc20"]`,
`fromBlock=toBlock=hex(block)`, hex `maxCount`; one `toAddress`/`fromAddress` each):
the professional liquidator's funding usually balances to exactly zero, so the profit
is the leftover leg (funding = repay + profit).

Measured 2026-11-08 (run bd3a4988, Base, moonwell core):

- mcbXRPL whale, tx `0x6fc9877a1aa7241d7ca3649a58588bc818c20830c53069c3892eb62fa7d2cf74`
  block 54167202: funding USDC 2923.322372 = repay 2750.873418 + profit 172.448954
  (6.27 pct of the repay) — the profit margin a collateral route earns.
- Supported-route whale, tx `0x7ae200e3302dd19f1af51faeb7e2b3b5635c461ca97464c2a5c40fe9a58c4f74`
  block 53786333: redeem USDC 7.0016 -> swap WETH 0.003141082572 = flash 0.002945867630
  + Morpho fee 0.000195214941; profit ~1e-6 ETH because the debt exceeded the collateral
  and the incumbent repaid the full debt, not a half-shortfall.
- mAERO-flash dust event, tx `0xd8e1aa1c9cc7c3c5eab6bbf2d142a11194118bcf9520344b07c280b348ff5c3a`:
  swap output AERO 0.232577463693 - flash AERO 0.219936076736 = 0.0126 AERO profit (< $0.01).

Pitfalls:

1. `repayAmount` raw units are the BORROW underlying's decimals (USDC 6; AERO, WETH,
   EURC 18; WADO 8). The ledger `LiquidateBorrow` fields carry no borrow-market field, so a raw
   magnitude is meaningless until the transfers name the borrow asset (the flash and repay
   legs show it).
2. mToken redeem pays `redeemTokens / exchangeRate`: the mature Moonwell mUSDC and mWELL
   exchangeRates are ~41 and ~49, so a tiny USD redemption does not imply small
   `seizeTokens` (and vice versa).
3. `"token"` is not a valid Alchemy category (HTTP 400 lists the valid set) — use
   `["external","erc20"]`.
