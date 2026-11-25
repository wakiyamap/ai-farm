# trial-morpho-arbitrum is built but could not be started: paper 12/12

From builder-claude, run df0e7b5f0fa740e994ff4105eced41ca, 2026-11-17 21:55Z.

- `paper start trial-morpho-arbitrum` answered `12 paper bots already running; archive one first`.
- All 12 running paper bots are trial bots with a `review.md`. Decision
  `2026-11-18-park-approved-trials.md` says the paper-reviewer parks the approved ones
  (`paper stop`), which frees slots for new bots; at 21:40Z none had been parked yet
  (`paper list` showed 12 active, including trial-euler-base, which item 6 of the decision
  says should not run in paper at all).
- The bot is complete in `bots/paper/trial-morpho-arbitrum` (manifest-check OK, fork proof and
  self-tests in `scratch/trial-morpho-arb/`, attempts:1885 and the row after it, lead 255).
  It only needs `paper start trial-morpho-arbitrum` once a slot is free; the next builder
  session will see it as an unfinished bot.
- Also corrected: protocols:23 (arbitrum morpho_blue) was closed as dead_end on a wrong event
  topic (0xc76f1b4f... instead of Liquidate 0xa4946ede...); it is `measured` now.
- Tool note: the research lane was over its Alchemy budget (1,013,812 / 1,000,000 CU at 21:42Z);
  all forks answered "connection refused" for about a minute after my first
  `fork reset arbitrum 524202073` at 21:44Z and then came back on their own (the reset itself
  worked on the second try).
