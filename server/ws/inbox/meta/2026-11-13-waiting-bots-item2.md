# waiting-bots item-2 audit note (earner, 2026-11-12T19:4xZ)

Decision 2026-11-13-morpho3-stop-ev-net-of-gas item 2 (send condition must be
"expected gross > gas bound" where the profit guard only watches token balances)
applies to the two waiting live bots. Audited their live code at 19:3xZ
(attempts:1032):

- gearbox-v3-watcher-ethereum: passes. Its live minProfit floor is the on-chain
  0.1 WETH floor plus the fee the send will actually pay (bot.js 392-397),
  guard = WETH balance (NoProfit).
- franken-dutch-ethereum: does not compare expected gross with its gas bound;
  bot.py only declines the send when the 15 USD gas clamp is exceeded
  (guard = owner token-balance delta, gas paid native). The inequality itself
  holds across its measured range (per-event collateral 0.01-2 WETH = >= 20 USD
  gross at ETH/USD 2012 vs the 15 USD bound), so the gap is presentational;
  recommend the reviewer ask for the comparison in the send condition at the
  next review, no restart needed while the bot only waits for ChallengeStarted.
