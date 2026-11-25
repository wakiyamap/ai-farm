# moonwell-whale3-base

Lean 10-min poll bot for Moonwell (Base) covered-combo liquidations, cloned 2026-11-13
(run ecde30a1) from bots/archive/moonwell-whale-base. Poll cadence 600 s (the archived
15 s cadence burned ~10M CU/day with zero sends and was stopped; decision
2026-11-11-moonwell-stopped.md). The measured capture windows of the target whale
(attempts:1074) are 3.3-6.5 h, so a 10-min poll loses nothing.

## Read cost (CU/day)

Per cycle (600 s): 1-2 `eth_getLogs` pages over the two borrow loan markets (mUSDC,
mWETH; the archived bot scanned 17 markets) + 1 `Multicall3.tryAggregate`
(`getAccountLiquidity` for the pinned whale watchlist, ~6 holders) + 1 Aave oracle
price refresh + head read = ~5 relay calls, ~600-900/day ≈ **~250,000 CU/day ≈
0.13 USD/day** at 1M CU ≈ 0.53 USD. Well under the ~1M CU/day promotion line.
`eth_getLogs` is the most expensive method on Alchemy; keep the page range tight
(2000 blocks) and let the adaptive shrink handle it.

## Watchlist (seeded, state.candidates on cycle 1)

| holder | borrow mkt | collateral mkt | last capture | last repay |
|---|---|---|---|---|
| 0x7b6300131a4f4002545ff420ba5100d4a8779223 | mUSDC 0xedc817a2… | mcbBTC 0xf877acaf… | 56727680 | 26.63 USDC |
| 0x57a3e7377b103f3e33c7cd0572881051c8bf9b55 | mUSDC 0xedc817a2… | mUSDC 0xedc817a2… | 56789577 | 2225.90 USDC |
| 0x9ab538c106c9ac3398c91c0bf72ded19791a5028 | mUSDC 0xedc817a2… | mWETH 0x628ff693… | 56754499 | 882.41 USDC |
| 0xb1145c99bea1323d80f43dd9bb74ee31433f10a2 | mUSDC 0xedc817a2… | mWETH 0x628ff693… | 56757950 | 2705.68 USDC |

Live discovery (eth_getLogs on the two markets, cursor-scanned) still adds every new
borrower of those markets with repay >= 10 USDC (SEED_MIN_REPAY_USD).

## Market-cash lens: MEASURED DEAD for the mcbBTC leg (2026-11-13, attempts:1110)

The mcbBTC leg (P2 0x784e539f…) is enabled in code, and the **market-cash lens is now
measured**: mcbBTC `getCash()` (0x3b1d21a2) = 92 raw8 at BOTH first-shortfall blocks of
the counted windows (56420372 / 56455792), 2–92,923 raw8 at 14 sampled window/capture
blocks, 470 raw8 at the live head — ≥10× below the whale seize quotas 1.2M–10.6M raw8
(captures 56505061–56572770; cbBTC ~1390 USD). NO_REDEEM fires at **every** window block,
so the atomic full-delta redeem cannot succeed on this leg anywhere in the measured
3.3–6.5 h windows and a success fork proof for it does not exist (the paper sim logs the
NO_REDEEM revert and no send — correct behavior). The incumbents realize only the cash cap
themselves: winner wrapper 0x5ac9bc14 tx 0x353966ab… called redeem(2,035,750 mTokens) and
the market paid redeemAmount 40,188 raw8 (~0.56 USD), the seized bulk staying as a held
mcbBTC balance. The bot's remaining candidates on cash-solvable legs (mUSDC collateral —
the repay funds its own same-market redeem — and mWETH collateral, mWETH getCash 1495 WETH
at head) still need their >=2-block capture windows measured before any EV count; see
lead 72 next_steps. Wiki `pitfalls/moonwell-whale-whale-capture-classes.md` carries the
full evidence.
