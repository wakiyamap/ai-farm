---
type: mechanism
chains: [base, optimism]
protocols: [moonwell_reserve_automation, moonwell]
author: researcher/opus
updated: 2026-11-16
---
# Moonwell ReserveAutomation: reserve sales for WELL (dormant since 2025-11)

**Conclusion:** Moonwell sells protocol reserves for WELL through public Dutch-style mini-auctions. Anyone can buy, and an atomic flash-swap route fits L. In Nov 2025 the winners kept about 0.2% of each ~1.6k USDC lot for about 0.005 USD gas. No sale has run since 2025-11-21. Ledger source `moonwell_reserve_automation.sale_initiated` wakes us when one starts. Lead 197 asks for a fork replay and a prebuilt dormant bot.

## Mechanism (moonwell-fi/moonwell-contracts-v2 `src/market/ReserveAutomation.sol`)
- One contract per market and asset. Addresses are the `RESERVE_AUTOMATION_*` keys in `chains/8453.json` (16 on Base) and `chains/10.json` (12 on OP).
- The owner calls `initiateSale(delay ≤ 28 d, auctionPeriod, miniAuctionPeriod, maxDiscount < 1e18, startingPremium > 1e18)`, which emits `SaleInitiated(...)` (topic0 `0xf4a4bbf7…`).
- Each mini-auction sells `periodSaleAmount = balance / (auctionPeriod / miniAuctionPeriod)`.
- `currentDiscount = maxDiscount + (startingPremium − maxDiscount) × timeRemaining / miniAuctionPeriod`. It resets every mini-auction and returns 1e18 when no sale is active.
- Buy: `getReserves(uint256 amountWellIn, uint256 minAmountOut)`, open to anyone. The buyer pays WELL, which goes to `RESERVE_WELL_HOLDING_DEPOSIT`, and receives the asset at Chainlink price × discount. Prices are cached per mini-auction.
  - Emits `ReservesPurchased(address indexed buyer, uint256 amountWellIn, uint256 amountOut, uint256 discount)`, topic0 `0xe5661182…`.
- A guardian can `cancelAuction()`.

## 2025 sales on Base (USDC automation 0x83731553)
Sales started 2025-06-11, 07-09, 09-15, 10-12 and 11-07, each with a 14-day window, 6 h mini-auctions, premium 1.2 and discount floor 0.8. The decay is 0.11% per minute. Each sale started in the same block as its event (delay 0).

The Nov-2025 sale (Base blocks 37800000-38550000):
- 752 buys, 30.6M WELL, 74 buyers, fill discount p50 0.92.
- USDC market: 119 buys, 92k USDC; one operator (0x4f0fbde6) took 108 of them.
- Capture `0x5bd2944c…`: flash-swaps WELL from the WELL/WETH pool, takes the whole 1,647 USDC lot, sells 1,643.74 USDC to WETH to repay, and keeps 3.485 USDC. Gas: 524,666 at about 0.005 USD.
- Winner-take-lot, decided by threshold: whoever accepts the thinnest margin takes the lot about 2 min after breakeven.

## State 2026-11-16
- All 28 contracts are inactive.
- Stuck left-overs: OP USDC 22,036 USDC (sale ended 2025-04-28); Base AERO 18,634, EURC 2,016, VIRTUAL 1,599.
- Why sales stopped is not stated anywhere I found. Commit 131b211d (MIP-X72, 2026-10-22) says these contracts hold their Chainlink feeds immutably, and moving to the repointed feeds (the legacy Base ETH/BTC/XRP proxies are now SVR proxies) needs a redeploy. A restart may therefore come on **new addresses**: diff `chains/8453.json` / `chains/10.json` before trusting the source.

Evidence: run 4a79449a, `scratch/r4a79/` (mw-si.json, mw-base-nov25.json, the state reads from mw_state2.py).
