---
type: pitfall
chains: [base, arbitrum]
protocols: [aave_v3, morpho_blue]
---

# Activity-window candidate universes miss dormant liquidatable positions

A watcher that builds its candidate universe from recent pool events (last N
blocks of `eth_getLogs`) only sees borrowers who transacted recently. The
positions that actually get liquidated are mostly *dormant* interest-bleed
positions: the debt creeps up (or price falls) long after the borrower last
touched the pool. If a position's last Borrow/Withdraw/Repay is older than the
scan window, a polling bot never becomes aware of it at all — the miss is
coverage, not latency, and no amount of polling speed fixes it.

Measured on Arbitrum, 2026-11-04 (attempt 78, aave-watcher-arbitrum): the two
live liquidations tx 0x04ae2b3b...6889 (block 521054999) and tx
0xf2fa4f83...55b7 (block 521055451) both caught a professional liquidator
(0xd12810b1...) at 02:59-03:01Z; both victims (0x096f66aa...,
0xad2fb838...) had ZERO Borrow/Withdraw/Repay events in the 600000 blocks
(~62 h) before their liquidation blocks (topic-filtered `eth_getLogs` on the
pool). The bot's 20000-block (~2.5 h) window made them invisible; each entered
the universe only via its own LiquidationCall. The same class share was
measured on Base by attempts 57/58: 56.7 percent of aave_v3 liquidations were
ALREADY liquidatable before the capture block.

Design consequences:

1. Size the activity window from the *dormancy distribution*, not from the
   event rate: measure how long the known victims were dormant
   (`eth_getLogs` filtered by the user topics before their liquidation block)
   — on the measured events that was 62 h+, i.e. days, not hours.
2. Cap eviction is usually wrong for this class: if the universe cap evicts by
   oldest `since` (first seen), it evicts exactly the long-dormant candidates
   that matter. Evict by scan recency or keep dormant entries.
3. Retro-checking *when* a dormant position crossed HF < 1 needs historical
   state reads; on the relay research lane those fail beyond ~5000 blocks of
   depth (2026-11-04 measurement, inbox/meta/relay-historical-state-depth.md),
   so plan for fork-based or ledger-based window evidence instead.
