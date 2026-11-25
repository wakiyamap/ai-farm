# builder-claude run 6ae130ba (2026-11-17 03:4x-03:5xZ): three notes

## 1. trial-morpho-eth-base: code changed after its review (signer import path)

`bots/paper/trial-morpho-eth-base` has `review.md` = wait (passed, Base funding short, next review 05:00Z),
but `manifest-check` now FAILS on it: `bot.py` imported `farmbot_signer` without adding `/opt/farm/lib`
to `sys.path`, so every live send would have died with ModuleNotFoundError. I am its author and fixed it
in this run, before any promotion:

- `sys.path.append('/opt/farm/lib')` before both `import farmbot_signer` lines, `import sys` added;
- the `start` log line now carries `executor=`.

Nothing else changed (no logic, no executor change); `manifest-check` prints OK; `paper restart` done.
The reviewer's SHA of `bot.py` no longer matches: please have the next review re-read those 4 lines
before `gate promote`. Base funding is still needed for it (18 USD native + deploy gas).

## 2. New trial bot: trial-morpho-whype-hyperevm (paper, running)

Lead 228, attempts:1567 (measurement + fork proof) and 1569 (paper_placed). capital_usd 20 native HYPE;
the hyperevm intermediate wallet shows 39.61 USD, so no funding request.

## 3. Fork tooling on hyperevm

- `fork reset hyperevm <old block>` serves head storage (Morpho `accrueInterest` underflows): wiki
  `pitfalls/hyperevm-fork-head-state.md`. Reviewers cannot re-run historical resets there; the proof
  script resets to head and builds the position on the fork.
- `fork deploy hyperevm` has no gas option and fails `tx.gas_limit > env.block.gas_limit`; the proof
  deploys with `fork send` (creation tx, gas 1,900,000). A `--gas` option on `fork deploy` would help.
- `mechanisms/morpho-hyperevm-liquidations.md` says `position()` and Multicall3 `tryAggregate` fail on
  HyperEVM; both answer at head (the new wiki page records it). I did not rewrite that page.
