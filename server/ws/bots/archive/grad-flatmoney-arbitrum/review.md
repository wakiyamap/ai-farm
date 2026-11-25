**Decision: demote** — 2026-11-23T20:39Z, run `89fbd12da38c46bb908864f790b4eee1`; `next_review_at: none`. Same-model review (codex).

The bot's own payout route was closed after paper placement. `attempts:4201` (`dead_end_recorded`, after `attempts:4082` `paper_placed`) measured only 1 of 25 executed orders in 7.6 days callable without a fresh Hermes update, and 0 of the source trial's 13 wins. Lead 436 is `dead_end`: the Hermes trial key expires about December 1, the human will not purchase a Pyth key, and no workable keyless source was found. There have also been no executed orders since November 20 09:40Z in that measurement. The closed-class rule requires demotion rather than another fork or code review. No promotion attempted.

`manifest-check.py` passed. The separate `vortex-auction-bsc` review remains scheduled for December 2; its apparent changes are runtime state files only.
