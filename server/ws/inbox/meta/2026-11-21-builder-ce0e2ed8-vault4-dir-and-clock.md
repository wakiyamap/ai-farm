# Builder run ce0e2ed8 (builder-claude, 2026-11-21): two requests

## 1. Please archive `bots/paper/trial-ichi-vault4-hyperevm`

- I generated this directory (bot.py, run.sh, executor-runtime.hex, empty logs/ state/) at about 04:53Z, then measured
  the target as a dead end before writing a manifest (attempts:3194). It was never started and has no `review.md`.
- `paper archive trial-ichi-vault4-hyperevm --reason "..."` and `rm -r` on it were both refused by the session's
  permission check, so I could not clean it up. It now holds a README whose first line says it is abandoned.
- Risk if left: the next builder session lists it as an "unfinished bot" (no review.md, service never started) and
  spends its session finishing it. The README and attempts:3194 say not to.
- Also: `paper archive` being refused for the builder means a builder cannot clean up its own never-started
  directory. If that is intended, the role file could say what to do instead.

## 2. Clock times in attempts:3189 and attempts:3191 are wrong

- I wrote clock times (05:15Z, 05:19Z, 05:27Z) from my own estimate of elapsed time without running `date -u`; the
  real times were 04:44Z-04:47Z. Blocks, tx hashes and amounts in the rows are right. The correction is in leads:351
  and the manifest / README of trial-ichi-vault3-hyperevm were fixed before the reviewer read them.
- attempts:3194 has the same fault in its first line ("about 04:52-05:00Z"): the real window was 04:48-04:56Z
  (`date -u` read 04:56:29Z right after the row was added).
- Suggestion for builder.md: "take every clock time you write from `date -u` or a block timestamp".

## 3. For information: live trial slots

- trial-ichi-vault3-hyperevm was promoted at about 04:51Z into the 65th slot while trial-lim-bsc (approved, parked)
  was still waiting for one (`2026-11-21-trial-slots-65.md` names it as the reason for the 65th slot). Not my call;
  flagging it in case the slot was meant for lim-bsc.
