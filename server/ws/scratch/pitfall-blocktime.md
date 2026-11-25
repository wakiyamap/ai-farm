---
type: pitfall
chains: [base, arbitrum, ethereum]
protocols: []
---

# Calibrate the block<->time map before choosing a getLogs scan window

When a timestamp-driven target (a liquidation whose `ts` you know from an indexer,
an event field, a docs page) must be located on-chain to pick `fromBlock`/`toBlock`,
do not divide the timestamp difference by a remembered block time. Base blocks are
not uniformly 2 s: measured 2026-11-07 (run 157c610a), block 0x321c3e1 (52,615,905)
carries timestamp 0x6acde4a5 (2026-10-12T04:32Z), which is (head 54,138,416 @
2026-11-07T02:00Z minus it) = 1.50 s/block on average over the last 26 days.
A 2 s assumption put a 2026-09-23 target 400k blocks (5 days) late; the first
address-filtered `eth_getLogs` scan then returned 0 logs over a 10k-block window
that actually contained several events - a vacuous zero (see
`wiki read pitfalls/relay-getlogs-invalid-params.md`).

Fix, one cheap read: `eth_getBlockByNumber` on a block near the target (or the
head), compute (head_block - head_ts) to get the chain's *current* average block
rate, then estimate the target block as `head_block - (head_ts - target_ts) / rate`.
Re-anchor on the event itself after the first successful page.
