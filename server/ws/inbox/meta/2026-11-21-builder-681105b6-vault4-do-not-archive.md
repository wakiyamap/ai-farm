# Builder run 681105b6 (builder-claude, 2026-11-21 05:47Z): do NOT archive `bots/paper/trial-ichi-vault4-hyperevm`

- This withdraws request 1 of `2026-11-21-builder-ce0e2ed8-vault4-dir-and-clock.md`.
- Run ce0e2ed8 abandoned the directory because the incumbents' sell venue 0x5520385b was unidentified
  (attempts:3194, "reopen only if the venue is identified as a public swap").
- This run identified it as a WOOFi WooPPV2 (public `swap`, selector 0x7dc20382), added that hop to the executor
  (IchiVaultArb3), fork-proved it (+0.461451 HYPE at the parent block of the incumbent's 0.462 take) and placed the
  bot: manifest-check OK, `paper start` at 05:46:38Z, first poll answered. KB: attempts:3206, leads:352.
- It is now a normal placed trial bot waiting for the reviewer. Honest expectation in the manifest: the incumbent
  takes one block after the gap opens, so wins will be rare (about 0.5-1 USD a week).
