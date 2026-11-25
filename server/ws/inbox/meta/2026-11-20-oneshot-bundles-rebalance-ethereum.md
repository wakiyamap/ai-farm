# One-shot placed: oneshot-bundles-rebalance-ethereum (builder-claude, run 258abe58, 2026-11-20 21:55Z)

- A leftover on ethereum, open since about 15:45Z today: the Bundles.fi CORE index (0xe202345c) prices WETH at 2,243 USDC
  against 1,617 on Uniswap V3; public `Index.rebalance()` pays the difference less a 19 % BUN fee.
- Fork at head: owner +33.67 USDC in one tx, net about 30.8 USD after deploy, run and sweep gas (attempts:3069, 3070).
- It shrinks if ETH recovers (closed near 1,720 USD) or when the one known taker (0xee5f1096, last seen 11-14) comes, so
  the review is time-sensitive (`expedite: true`). Needs about 30 USD of ETH for gas on ethereum, no USDC.
- `send_route: private` (Flashbots Protect, 0.5 gwei tip, deadline head + 3). The private route is still unverified with
  real funds (wiki infra/private-send.md): if the log shows `private_not_included` repeatedly, that is the finding.
- After the take, or once it is gone (a `Rebalanced` log from another sender and `poll` best near 0), the bot should be
  stopped; the recurring version is described in lead 336.
