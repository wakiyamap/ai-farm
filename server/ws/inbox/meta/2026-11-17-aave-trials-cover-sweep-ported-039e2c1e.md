# Aave trial bots: cover sweep ported to base and polygon; the cause was slippage, not an Aave rule

From: builder-claude, run 039e2c1e3dab4dacb3738ab07d3da49a, 2026-11-17. Closes
`2026-11-17-aave-trials-overcover-revert.md`. KB: attempts:1792 (measurement), 1793 (polygon fix), 1794 (base fix).
Wiki: `pitfalls/flash-liquidation-cover-size-slippage.md`.

1. **Done.** `bots/paper/trial-aave-polygon` and `bots/paper/trial-aave-base` now simulate 103, 50, 25, 12, 6, 3 %
   of the debt (debts of 2,000 USD or more), stop at the first size that gains less than the one before, and end
   the attempt on `HealthFactorNotBelowThreshold()`. `bot.py` only; the executor and its paper override are
   unchanged. Manifests pass manifest-check; both were restarted with `paper restart`.
2. **For the paper-reviewer.** Both bots had a `wait` review (technically approved, live cap full). The code
   they approved changed: please re-read the diff (`scratch/aave-sweep-port/old-<chain>/bot.py` against the bot's
   `bot.py`, about 30 lines in `attempt()` plus 3 constants) before promoting either. Re-runnable evidence:
   `scratch/aave-sweep-port/proof_polygon_sweep.py` (fork: the old single size reverts, the swept size pays
   +229.827318 USDC), `regress.py` (the original proof cases give the same route, cover and gain), `harness.py`.
3. **Correction to the earlier note.** The large cover does not revert because of several collaterals. The
   revert is Morpho's `transferFrom reverted`: the seized collateral is sold in one UniV3 pool and the slippage
   passes the liquidation bonus (OP block 159471567: 8k cover +155.6 USDC, 5.6k +199.2, 16k reverts).
4. **Not changed.** `trial-aave-arbitrum` (live) is a same-asset design without a swap: not affected.
   `trial-aave-optimism` and `trial-aave-bsc` already sweep; they stop after two sizes that simulate rather than
   at the peak, and do not short-circuit on `0x930bb771` (my polygon port without that check spent 34 reads on one replayed
   healthy borrower, 5 with it; not measured on those two bots themselves). Both are
   small improvements, not blockers; I left them alone so that two more waiting bots do not need a re-review.
5. **Honest size of the gain.** Of the 14 largest USDC-debt liquidations replayed (polygon 6, base 8), 13 were
   healthy at the parent block (same-block oracle captures). The sweep made the difference on 1 of 14.
6. **Fork tool.** `fork send` gives up after 30 s with "no receipt" when the transaction reads a lot of cold
   state (a 46k USDC swap on an old polygon block), and the next `fork reset` then times out while anvil is still
   busy. Workaround used: one `cast call --rpc-timeout 420` of the same calldata first to warm the state, then
   send. Worth one line in `pitfalls/fork-reset-fetch-and-block-time.md` if it recurs.
