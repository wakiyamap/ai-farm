# ledger: the emitter initialization stall is fixed (phase 10h, human, 2026-11-11)

Answer to inbox/human/2026-11-10-meta-ledger-emitter-init-stall.md (meta 421c68f0, researcher run
3da38c54). Thank you for the measurement; it pointed straight at the cause. Nothing here needs a
decision.

## Cause

Neither of your two guesses exactly. Nothing failed at the 10th or 12th address. ledger-ingest read
every emitter of a source with its own `eth_getLogs` (60 CU). A source therefore paid 60 CU per
emitter and run just to keep its initialized emitters at the head. With the 600 CU share of an
agent source that is 10 emitters: the 11th got one call per run, the 12th was never initialized,
and a second chain of the same source (beefy's arbitrum) was never reached. The stall was
permanent, not slow.

## What changed in /opt/farm/bin/ledger-ingest

- All emitters of a (source, chain) that stand at the same block are read with **one**
  `eth_getLogs` (address list). At the head a source costs 60 CU per chain and run, whatever the
  number of emitters. The budgets are unchanged (6,000 CU per run for agent sources, at least 600
  per source).
- A lagging emitter (new, still backfilling) is advanced first until it reaches the others. While
  that backfill runs, the emitters already at the head wait; they catch up in one call afterwards.
- Sources with `actor_field: tx_from`: when the budget ran out in the middle of a block range, the
  cursor used to move past the whole range and the remaining events of that range were lost. The
  cursor now stops at the first block that was not stored. **Events lost this way before 10h are
  not recovered**: for a tx_from source added before 2026-11-11, a gap inside the backfill window
  is possible. If such a source matters to a claim, say so in inbox/human and the human can rewind
  its cursors.

## What to expect

- `python3 tools/ledger-source-coverage.py` should reach initialized = configured for both sources
  within a few runs (initializing costs 20 CU per emitter).
- Reaching the head takes longer: about 50 calls for 7 days of ethereum and about 240 for 7 days of
  arbitrum, per group of emitters, at roughly 10 calls per run. Ethereum: a few hours. Arbitrum:
  most of a day. Until a cursor is at the head, zero events is still no evidence, as you wrote.
- A source with up to 20 emitters per chain is now fine. The limits (20 addresses per chain, 40
  agent sources) are unchanged.
