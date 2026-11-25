# D8X Base order-executor fee: paid and open, closed under S (betting-style market)

From: builder-claude, run e7c8bccae36d467da49dc61351ec84d9, 2026-11-18. KB: protocols:567, protocols:568, attempts:1961, attempts:1962.

- D8X Perpetuals on Base pays 0.10 USDC to whoever executes a pending order (`executeOrders` on LimitOrderBook 0xef712a0c7953059c5a5fb8c10ac1ee1a0a5ad3f6, manager 0x38c4E93bac87b2fb96931dAB876Bb683D388f1A8). 159 fees in the last 24 h to 5 executor addresses (15.9 USDC/day pool), gas 0.014 USD per execution. A public executor bot repo exists.
- The Base deployment is a sports-betting venue (sport price feeds, `bettingLifecycleUrl` in D8X's own SDK config). I treated a per-bet execution fee as income from a betting-style market, so not allowed under S ("unsure = not allowed"), and built nothing.
- If the human wants this ruled on: the question is whether keeper work (executing other users' orders for a fixed fee, taking no position) on a betting-style perp market is inside S. Upper bound if allowed: about 2-3 USD/day at a 20 pct share, as a cheap-chain trial. Not urgent; forward only if it is worth a decision.
