---
type: method
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [any]
author: meta/opus
updated: 2026-11-14
---
# Taker types: how the winner detected the case (decision 2026-11-14-taker-types-pull-oracle)

**Conclusion first:** every liquidation case an earner measures (census timing, crash post-mortem 1-2, rival-contract reading 2-3) gets one taker type next to its seconds: **P / B / O / S / T / unknown**, with the tx hash that shows it. B and O are class D (not copyable). P, S and T are not dismissed as "fast": each has its own next step below. Never fill a type by guess; write "unknown". Source: `decisions/human/2026-11-14-taker-types-pull-oracle.md` (Japanese; it wins if this page disagrees).

## The types

| type | what the tx shows | evidence to write |
|---|---|---|
| **P** pull oracle | the taker updates the oracle price inside its own liquidation tx (Pyth update call, RedStone signed price appended to calldata, Chainlink Data Streams report). Trigger = off-chain price stream, not an on-chain event | capture tx hash + which marker (below) |
| **B** backrun | the capture sits in the same block right behind a separate oracle-update tx, at most 2 txs in between | update tx hash, both tx indexes, any `block.coinbase` transfer |
| **O** auction | the price update goes through a mechanism that sells the right to liquidate (Chainlink SVR, FastLane Atlas `metacall`, ...) | which mechanism; whether the market's feed is Standard or SVR, from a primary source |
| **S** spray | the same sender repeatedly sends failed or no-op txs at the same market | success and no-op counts over the window, gas of one no-op in USD |
| **T** time-driven | the case became takeable without a price update (interest accrual, maturity, auction start time) | the trigger, and whether its time was computable in advance |
| **unknown** | none of the above shown | what was checked |

Markers for P (any one): Pyth `PriceFeedUpdate(bytes32,uint64,int64,uint64)` log in the receipt; Chainlink Data Streams `ReportVerified(bytes32,address)` log; RedStone payload marker `000002ed57011e0000` at the end of calldata. Get topics from `cast keccak`, and run a same-shape positive control before a zero (`infra/pull-oracle-markets.md` has one for Base Pyth).

## What each type means for farm

- **B, O → D.** Farm does not watch the mempool, send bundles, send to builders directly or bid for liquidation rights.
- **P → not out by speed alone.** The pull-oracle market list (`infra/pull-oracle-markets.md`, researcher) decides whether a price-stream receiver is worth building; a P bot is class C until the human says otherwise. Time a P case from "off-chain price crossed the liquidation line" to inclusion, only where the stream's history is public and keyless; else write "not measurable". Earners time at most 10 per protocol (5 largest gross, 5 smallest).
- **S →** net per day over the window = successes x net - no-ops x no-op gas; next to it farm's cost to do the same (L, gas, Alchemy CU). The human decides whether to build.
- **T →** if the trigger time was computable in advance, classify the case under race-rule-seconds from that time, not from the capture block. A counted case is a lead (like lead 44).

## Where to write it

- On each measured case (attempts row, crash page row, card).
- On each operator card `infra/bot-census/<operator>.md`: one line, cases per type.
- Crash post-mortem table (`infra/crash-2026-11-14.md`): count and gross per type per source x chain, and in the conclusion the share of gross taken by P+S+T vs B+O.

## Feed bots: precompute the liquidation price (decision item 3)

A feed bot that waits for price updates keeps, per watched position, **the price at which it becomes liquidatable**; on an update it compares against that table instead of re-reading every position. The table is updated on collateral / debt events (supply, repay, borrow, ...) and rebuilt on the 5-10 minute safety poll. Positions that cross by interest accrual get a precomputed **crossing time** (type T). The profit check before sending is the executor's revert, not extra bot-side reads. A reviewer answers `fix` to a feed bot that re-reads all positions on each event. This is a build rule; it does not change how EV is counted.
