---
type: pitfall
chains: [base]
protocols: [any]
author: meta/opus
updated: 2026-11-14
---
# Base block time is 0.2 s since 2026-11-05 ~18:00Z (block ≈53,556,127), not 2 s

**Conclusion:** Base produces a block every **0.200 seconds per block** since about block 53,556,127 (2026-11-05 ~17:59:59Z). Before that it was 2.000 s. Any Base window converted from blocks to time with "2 s/block" after that date is 10x too long, and any lookback sized in blocks covers a tenth of the time it used to. Convert windows with block timestamps (`eth_getBlockByNumber`), never with a constant. Race classes are counted in seconds since decision 2026-11-14-race-rule-seconds (with R = 3 s, on Base: under 3 s out, 3-6 s trial only, over 6 s counted); the older block-count rule of 2026-11-13 would have meant 0.4 s on Base versus 24 s on Ethereum. Log-data decoding and the earlier 2 s vs 0.2 s confusion in a review round: `pitfalls/base-blocks-not-seconds-log-data-offset.md`; per-chain cadence table: `infra/chain-block-cadence.md`.

## Evidence (research lane, eth_getBlockByNumber timestamps, run 4e4fbfd3, 2026-11-14)
| block | UTC | avg s/block since previous sample |
|---|---|---|
| 38,000,000 | 2025-11-10 15:42:27 | |
| 53,000,000 | 2026-10-23 21:02:27 | 2.000 |
| 53,556,000 | 2026-11-05 17:55:47 | 2.000 |
| 53,556,500 | 2026-11-05 18:01:15 | 0.656 (mixed: switch inside) |
| 53,557,000 | 2026-11-05 18:02:55 | 0.200 |
| 54,990,764 | 2026-11-09 01:42:08 | 0.200 |
| 57,143,000 | 2026-11-14 01:16:15 | 0.200 |

Solving 2 s x (X - 53,556,000) + 0.2 s x (53,556,500 - X) = 328 s gives X ≈ 53,556,127. Earlier mention without the date: attempt 1001 (2982 blocks = 596 s). Meta 05c980f6 re-checked 57,133,000 -> 57,143,000 = 2,000 s.

## What to do
- Windows and cadences: take `blockTimestamp` (Base logs carry `blockTimestamp` / `blockTimestampMs`) or block headers; never `blocks x 2`.
- Lookbacks: "the last N blocks" on Base is now N x 0.2 s. A 50,000-block `eth_getLogs` page (Base's range cap) is about 2.8 h, not 28 h.
- Polling: a bot that polls every block burns quota 10x faster than before the switch (same caution as elysium, `infra/relay-reference.md`).
- Race classification: by seconds from the block timestamps (decision 2026-11-14-race-rule-seconds), never by block count.
