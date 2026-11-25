---
type: infra
chains: [ethereum]
protocols: [morpho_blue]
---

# Farm reaction time: ethereum (measured)

Conclusion: on ethereum the farm's measured end-to-end reaction time (event became visible in a
block → transaction sent) is **3.9 s**, and the transaction landed in the NEXT block (~8 s before
its inclusion). The race rule's default R = 3 s (decision 2026-11-14-race-rule-seconds.md) is
slightly optimistic against this one measured sample; for feed-wake cases the honest earliest
send is block-timestamp + ~3.9 s, i.e. still the next block at ethereum's ~12 s cadence.

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
