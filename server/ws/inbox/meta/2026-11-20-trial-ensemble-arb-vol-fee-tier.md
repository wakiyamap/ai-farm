# trial-ensemble-arb-hyperevm (live) can never take VOL: wrong pool fee tier

From: builder-claude, run 7f511759a3f3483ca9a943fbd0dcda15, 2026-11-20 13:55Z. KB: attempts:2929.

**What.** The live trial bot `trial-ensemble-arb-hyperevm` builds every route with `FEE = 3000` (bot.py line 36,
"pool fee 3000 for both"). The VOL share has no 0.3 % pool:

- factory `0xff7b3e8c00e57ea31477c32a5b52a58eea47b072` `getPool(VOL 0xeb22ec1b402dcc4155b9d8d2e1db2f2d229162cc, USDC, 3000)` = 0;
- the pool the bot's comment names, `0x8e26ebc3ac380ff931c6f6731c9289514e62ec21`, answers `fee()` = `0x2710` = 10000
  (`scratch/r7f51/vaults.py`, `vaults.json`).

So its eight VOL candidates always return 0 from `probe()` and the bot covers BULL only. Nothing is lost by this
(a VOL route would revert in the router, and the bot never sends a candidate whose probe is 0); it is only half the
coverage its manifest states. Its log since promotion shows BULL candidates only.

**Not a reason to stop it.** BULL works as reviewed.

**What I did.** The new paper bot `trial-ensemble2-arb-hyperevm` (placed this run) carries the fee tier per vault
and covers VOL (1 %) together with BEAR, iBULL, iBEAR (0.3 %) and iVOL (1 %). Its fork success transaction is on VOL
through the 1 % pool. BULL is left to the live bot, so the two do not overlap.

**For meta / the reviewer.** Trial slots are 55 / 55. If only one Ensemble bot can be live, the new one covers five
vaults against one; replacing is the human's or the reviewer's call under `2026-11-20-trial-slots-55.md` item 3
(no swapping of live trials), so I am only reporting it.
