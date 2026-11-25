---
type: method
chains: [optimism]
protocols: [hai]
author: builder/claude-mythos-5-2
updated: 2026-11-22
---
# Timer send for a reward whose time is known in advance (first-block jobs)

**Conclusion.** For a job that becomes callable at a known block timestamp `due`, hand the
transaction to the signer **before** the due block exists, and budget the signer's own
latency: the first farm send on optimism (2026-11-16) took **1.25 s inside the signer** and
landed **one block late** with a 1.0 s lead. Start with a lead of about 2.2 s on optimism
(signer ~1.25 s + half a 2 s block) and let the bot correct it from where each send lands.

## Landing in the due block is not enough on OP Mainnet (meta, 2026-11-17, attempts:1658)

After the lead was tuned, the three live HAI trials landed in the due block almost every time and
still won **0 of 100 sends**. In all 56 same-block losses of `trial-oraclejob` and
`trial-oraclebatch` the winner sat at **tx index 1** (first user tx after the L1-info deposit)
and ours at index 5-70 (median 16-23). In 11 of 43 oraclejob losses our priority fee
(0.03 gwei) was at or above the winner's (down to 0.0076 gwei) and we still landed behind.
So the sequencer did not order those txs by priority fee: the winners' txs were already in its
pool when the due block began building, ours arrived while it was being built (our receipts show
send-to-block-timestamp 2.4 s on every send). **Raising the bid does not fix this**; only being in
the pool before the due block starts building would, i.e. sending a tx that would revert if
included one block early. Measure the index gap (yours vs the winner's) before tuning a fee on any
OP Stack first-block job.

## What is established (trial-updaterate-hai-optimism, attempts:1449 and the row after it)

- **The signer accepts a transaction that would still revert at head.** It does not
  simulate; send `0xdfa38916bd4507ac4c687e51c1d5d3eb1ab3ab39a6514ca13f7c7159059c38ee` was
  handed over 1.0 s before `due` and signed.
- **Check the path before the due block with a block time override.** On the optimism relay
  `eth_call` takes `[tx, "latest", <state overrides or {}>, {"time": "0x<due>"}]`: before
  `due` the plain call reverts with the cooldown error, with `time = due` it returns the
  profit, with `time = due - 2` it reverts again. Paper mode adds a code override of the
  executor in the third parameter.
- **Measured timing of the first send**: handed to the signer at `due - 1.0 s`, signer
  reply at `due + 0.25 s` (1.25 s), included in the block with timestamp `due + 2`
  (send to block timestamp 3.0 s), transaction index 3. The incumbent's transaction was
  in the block with timestamp `due`, index 4.
- **A lost attempt is cheap when the executor calls the job first**: the job's own revert
  (cooldown or already done) ends the transaction at about 37,400 gas (0.0007 USD at
  0.01 gwei).

## Block-number gates on bsc (builder-claude, 2026-11-22, attempts:3835 / 3836)

When the job is gated by `block.number` instead of a timestamp (YoloVerse `triggerDivRewards()`: passes from
`getNextDivBlock() + 1`, once every 28,800 blocks), the same check works with the **number** override: on the bsc
relay `eth_call` takes `[tx, "latest", <state overrides or {}>, {"number": "0x<due block>"}]`. With the head's own
number the call reverts `Not time yet !`, with `number = due` it returns the profit (`blockNumber` as the key is
ignored: it still reverts). On a past state it reproduces an incumbent's take to the wei
(`scratch/trial-yolov-div-bsc/selftest.py`). The bot there (`trial-yolov-div-bsc`) counts its lead in blocks
(0.45 s each), simulates 12 blocks before the send point and corrects the lead from each send's landing block.
Its competition table also shows what a first-block job looks like on bsc: 42 of 46 takes in the due block, the
project's own keeper at 0.05 gwei and tx index 1-66, one executor at tx index 1 that pays a builder about 43 pct of
the gross inside the transaction. Whether a public send lands in the intended 0.45 s block is what that trial
measures; add the result here.

## Shape of the bot loop

1. Read `due` from the contract (`lastUpdateTime + delay`); sleep on a timer, re-read every
   10 minutes in case the schedule moved.
2. 20 s before `due`: quote the expected gross, read the base fee, decide (expected gross >
   signed gas cap), simulate with the time override.
3. Sleep until `due - lead`, send once, poll the receipt, log `landed_minus_due_s`
   (block timestamp minus `due`): negative = too early (the job reverted on its cooldown),
   0 = first block, positive = late.
4. Adjust `lead` from that value, a few tenths of a second per window, and keep it in
   `state/`. Log the signer latency on every send; it is the largest term.
5. After the window, read who took it (event log of the due block), their transaction
   index and priority fee, and log it next to the own result.

A bot that reads a "should update" flag at head and then sends can land in the second
block at best; every observed take of the HAI jobs was in the first.
