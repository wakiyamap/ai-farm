---
type: pitfall
chains: [optimism, base]
protocols: [hai]
---
# OP Stack: a higher priority fee does not move you ahead of a slot-1 winner

**Conclusion.** On optimism and base, a reward that is taken at **transaction index 1** of the first
block where it becomes callable is not a farm target, not even as a cheap-chain trial. The
incumbent's tx is already in the sequencer's pool when that block starts building; ours arrives
while it is being built and lands behind it whatever fee we bid. Before building a first-block
job on an OP Stack chain, read the tx index of the last 20 takes: if they sit at index 1-2, stop and
record the lead `blocked_infra` (reason: slot-1 incumbent, OP Stack ordering).

## Evidence (meta, 2026-11-17, attempts:1658)

- Three live HAI trial bots on optimism (`trial-oraclejob-hai-optimism`,
  `trial-oraclebatch-hai-optimism`, `trial-updaterate-hai-optimism`), timer sends tuned to land in
  the due block: **0 wins in 100 sends**.
- In all 56 same-block losses (oraclejob + oraclebatch) the winner was at **tx index 1** (first user
  tx after the L1-info deposit), ours at index 5-70 (median 16-23).
- In 11 of 43 oraclejob losses our priority fee (0.03 gwei) was **at or above** the winner's (down to
  0.0076 gwei), and we still landed behind. The block was not ordered by fee across those txs.
- Our send-to-block-timestamp was 2.4 s on every send (signer about 1.25 s of that,
  `methods/timer-first-block-send.md`).
- The human stopped all three bots on 2026-11-17 and asked that no HAI-style race be built again
  on optimism or base.

## What does not fix it

- Raising the bid (shown above).
- A shorter lead alone: the signer's latency is the largest term and is outside the bot.
- Pre-sending a tx that would revert if included one block early is still a position race against a
  faster incumbent; it is not in scope (principle 2) and a trial budget does not change that.

## What is still fine on OP Stack

Jobs where the takes are spread over many blocks or indexes (no single slot-1 incumbent), and
liquidations or auctions whose winners do not sit at index 1 of the first takeable block. Measure the
index distribution first; it costs one `eth_getTransactionReceipt` per past take.
