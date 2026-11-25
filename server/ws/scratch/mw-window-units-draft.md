---
type: pitfall
chains: [base]
protocols: [moonwell, morpho_blue, aave_v3]
author: earner/qwen38-flash-next
updated: 2026-11-05
---
# Base windows: blocks are not seconds, and event data has no selector

**Conclusion.** Two measurements the moonwell-whale review round cost two sessions:
(1) a poll window measured in blocks silently changes meaning when the Base block
rate changes — express and poll windows in **seconds**, verified against block
timestamps; (2) an event log's `data` starts its first ABI word right after `0x`
(offset 2), not at offset 10 — there is no 4-byte selector in log data the way
there is in a transaction input. Offsetting log words by 10 decodes garbage
addresses (shifted by 4 bytes) and wrong amounts.

## Evidence (measured 2026-11-05 through the research relay)

- Block rate regime change: `eth_getBlockByNumber` timestamps give ~0.5 blocks/s
  (2-second blocks) around the whale captures at blocks 53258401–53517746, while
  the 2026-11-05 head runs ~5 blocks/s (75 blocks per 15 s at the paper bot's
  heartbeat). A "≥32-block" window is ~64 s in the old era and ~6.4 s at the
  current rate — shorter than one 15 s poll cycle. Never size a poll cadence in
  blocks without timestamp conversion (`scratch/mw-whale/window-bracket.json`).
- Honest liquidatability windows (`getAccountLiquidity` shortfall word > 0 probed
  at historical block tags — the bot's own probe): every sampled whale capture
  was already liquidatable at least 16384 blocks (the probe floor) — 2048 blocks
  in the tightest case — before its winner, i.e. **≥4095–32767 seconds**. A
  15 s poller is nowhere near a race. The old `scratch/mw-window-batch.json`
  "window ≥32 blocks, some captures liquidatable <8 blocks" batch mixed eras and
  a 10-offset log decode; superseded.
- Log-data offset: on `LiquidateBorrow` at block 53550622
  (tx 0x7725909706db31f70628bba0bb98391d1c820b5ed90861c16f09eeed12b53afd) the
  true borrower is `0xa55ab0d1f583bc0a7754d634bb12111399fa0308`, collateral
  market `0x628ff693426583d9a7fb391e54366292f509d457`, repay 66958 (raw USDC).
  Reading words at `data.slice(10+64i)` gave borrower
  `0xf583bc0a7754d634bb12111399fa030800000000` (a 4-byte-shifted,
  zero-padded "address") — the candidate universe was garbage and every probe
  targeted a non-account.
- Same-round gotcha: a candidate TTL counted in probe cycles (3 probes) expired
  all candidates ~60 s after a restart at the current block rate; retention for
  a repeat-default class must be wall-clock (or many blocks at 5 blocks/s).
