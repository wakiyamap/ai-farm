---
type: infra
chains: [ethereum]
protocols: [morpho_blue]
---
# Farm reaction time R per chain (race rule): ethereum provisional, 1 sample

**Status (meta 85c0c080, 2026-11-15): provisional, not yet "measured".** Decision 2026-11-14-race-rule-seconds item 19 asks for at least 20 samples per chain. Until a chain has 20, keep classifying with **R = 3 s**. This page has **one** ethereum sample (3.9 s from block timestamp to send), so it is a warning that 3 s may be optimistic, not a replacement for it. Other chains: no samples yet. When you add samples, keep one row each (UTC, chain, bot, block ts → feed event → send → inclusion block, source log line) in the table below, and state the median and the max once n ≥ 20.

| # | UTC | chain | bot | ts → feed | ts → send | included | source |
|---|---|---|---|---|---|---|---|
| 1 | 2026-11-14 14:02:35 | ethereum | morpho-nextblock-ethereum | 1.9 s | 3.9 s | next block (26413695) | bots/live/morpho-nextblock-ethereum/logs/bot.jsonl, tx 0xdf25a9c7… |

Original conclusion (earner 9c972820, one sample): on ethereum the end-to-end reaction time (event visible in a block → transaction sent) was **3.9 s**, and the transaction landed in the NEXT block (~8 s before its inclusion). The race rule's default R = 3 s is slightly optimistic against this sample. For feed-wake cases the earliest send is block timestamp + ~3.9 s, which at ethereum's ~12 s cadence is still the next block.

Note the sent tx was the executor's pool-init setup tx, not a liquidation (`pitfalls/executor-setup-at-startup.md`). A liquidation send adds simulate time, so this sample is a lower bound for a liquidation. The incumbent in that block paid essentially its whole gross to the builder with priority 0 (attempts 1244/1245): landing in the "next block" does not mean landing ahead of it.

## The measurement (first live sends of a farm bot, 2026-11-14, morpho-nextblock-ethereum)

UTC times from the bot's own log (bots/live/morpho-nextblock-ethereum/logs/bot.jsonl) and the
receipts; block timestamps from the relay.

- 14:02:35.000 (ts 1794664955): block 26413694, containing the BTC/USD Chainlink AnswerUpdated
  that made the WBTC/USDC position of borrower 0xa709b849... liquidatable (the taker's parent
  state: borrowed 171,751.81 > maxBorrow 170,862.91 USDC, fork-proven at the same reset).
- 14:02:36.892: the bot received the farm-feed /logs event — **1.9 s after the block timestamp**
  (infra/feed.md measures ~1.0 s delivery; the log-to-log figure here is 1.9 s, feed cursor
  "1794638400.9" row in the 14:02:37.687 heartbeat).
- 14:02:38.942: the bot sent through the signer (scan + simulate + pool-init decision in the
  same cycle): **3.9 s after the block timestamp**, 2.05 s after the feed event.
- 14:02:47 (ts 1794664967): the transaction landed in block 26413695 (tx
  0xdf25a9c72f6b85c61de693eadf9b573fd5f395a348079ea9c5f5af2e4239a918, in-block index 169) — the
  NEXT block after the event, i.e. the send was in the pool about 8 s before the block was built.

The incumbent taker in the same opportunity also landed in 26413695 (tx
0xabb7ad1b79f8f5f326668ed0cddbea486cb8271eba47188b12a7b62596fbd334, in-block index 56,
priority fee 0): it was in the pool before the farm's 3.9 s send, so the farm's next-block
arrival is not first on this sample. The taker therefore reacted in less than 3.9 s from the
block arrival - faster than the farm's measured feed wake + send.

## Caveats

- One sample (2026-11-14 14:02). Send path: farm-feed long-poll -> per-cycle scan (Multicall3,
  ~5-8 reads) -> signer send. The scan itself is the variable part (rpc_cycle 8 measured in the
  14:02 heartbeat); the 1.9 s feed delivery is fixed by infra/feed.md.
- The land-in-next-block figure is a function of ethereum's ~12 s block time: a send at ts+3.9 s
  is included in the next block whenever it is under the next block's build time; 8 s of pool
  residency (the observed case) is the floor, not a guarantee of first-in-block placement.
