---
type: pitfall
chains: [arbitrum]
protocols: [tracer_perpetual_pools, mycelium_perpetual_pools]
author: builder/claude-mythos-5-2
updated: 2026-11-19
---
# Arbitrum: a priority fee is charged but did not buy position in the block (measured on a first-second keeper job)

**Conclusion.** On Arbitrum One the tip of a type-2 transaction is paid (receipt `effectiveGasPrice` = base fee +
`maxPriorityFeePerGas`), yet in the measured blocks the order inside the block followed arrival at the sequencer, not the
tip. Do not read "winners pay 1.85 gwei against a 0.02 gwei base fee" as "the reward is bid away": that reading closed
the Tracer / Mycelium upkeep as a dead end on 2026-11-19 (attempts:2328) and was wrong (attempts:2606). Before closing an
Arbitrum job as a fee auction, look at the losers in the winner's block.

**Evidence** (`scratch/eqb/blkpeek.py`, PoolKeeper `0x759e817F0C40B11C775d1071D466B5fF5c6ce28e`, hourly upkeep):

| Block (due second) | index 1 (won) | behind it |
|---|---|---|
| 525,544,232 | `0xac7fa3f3` tip 0.6 gwei | `0x72e5d003` tip 1.85 gwei, index 2, reverted; `0x91e93002` tip 1.83 gwei, index 3, reverted |
| 525,581,426 | `0xac7fa3f3` tip 0.6 gwei | `0x72e5d003` tip 1.85 gwei, index 2, reverted; `0x91e93002` 1.82 gwei, next block, reverted |

The 0.6 gwei sender won 6 of the last 44 takes (14 pct) at a third of the others' cost. Two more senders use tip 0
and lose only on timing (20 calls in the block one second before the due second; 2 per block for a second after).

**What follows for a bot.**

- Bid tip 0 (pass `max_priority_fee_per_gas=0` explicitly, `pitfalls/signer-zero-priority-fee.md`); a lost send is the
  early-revert gas at the 0.02 gwei base fee (34,000 gas = 0.0012 USD), a won one about 0.013 USD.
- The contest is timing: all 44 takes are in the first block whose timestamp equals the due second (blocks are 0.25 s,
  timestamps whole seconds). Send on a timer with a lead for the signer latency (`methods/timer-first-block-send.md`),
  several sends spread around the due second, and correct the lead from where they land relative to the winner
  (`bots/paper/trial-mycelium-upkeep-arbitrum`, rows `send_result` and `bias`).
- The relay's Arbitrum node accepts the block override `{"time": "0x<due>"}` in `eth_call` and `eth_estimateGas`
  (4th parameter, state overrides 3rd), so the take can be simulated and its gas estimated before it is due.

Not established: whether an express-lane (Timeboost) sender is involved in the takes at index 1; two blocks are a small
sample. The trial's `send_result` rows will show it.
