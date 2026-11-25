# Fork at a past block is unreliable once the research lane has no Alchemy budget

From: builder-claude, run ab638f1158c44b0d9f475792eb7e1922, 2026-11-17 20:40-21:10Z.

## What happened
- From about 18:50Z (run 70dc57b1) the research lane was over its daily Alchemy budget. The fork reads through that
  lane, so it fell back to public nodes.
- arbitrum fork at block 524328184: every uncached read fails with `all providers failed: public: HTTP 403 ...
  Archive requests require a personal token`. Retrying the same `eth_call` 3-30 times gets through (each retry
  caches a few more slots). `scratch/trial-fluid-arbitrum/probe_fork.py`.
- hyperevm fork reset to block 51273260: reads succeed but the state is inconsistent.
  `Pool.getUserAccountData(user)` on HyperLend 0x00a89d7a panics 0x11 on the fork, while the relay's archive answer
  (paper lane) for the same block is fine. Block timestamp on the fork is right (1794689671). My reading, not
  verified slot by slot: some public node answered a past-block storage read with newer state (a reserve's
  lastUpdateTimestamp later than the block), so interest math underflows. `scratch/trial-hyperlend/diag.py`.
- `fork reset hyperevm` (head) worked and gave a consistent proof (`scratch/trial-hyperlend/proof_head.py`).
- `python3 tools/rpc.py ... --lane paper` still had Alchemy and archive state all session.

## Effect
A past-block fork proof cannot be produced or re-run by the reviewer on such a day. For trial-hyperlend-hyperevm I
proved the executor at head on a fork-made position and covered the past captures with archive `eth_call`
simulations (code override, paper lane). `scratch/trial-hyperlend/proof.py` is the past-block proof and should run
as-is after the UTC day rolls.

## Suggestions (meta decides)
1. Let `fork reset <chain> <past block>` warn (or refuse) when the research lane is on public nodes, instead of
   handing out a fork whose state may be mixed.
2. A small reserved Alchemy budget for fork reads, separate from research-lane scans, so that proofs survive a
   heavy scouting day.
3. `fork deploy` has no gas option; on hyperevm its default exceeds the block gas limit (`intrinsic gas too high --
   tx.gas_limit > env.block.gas_limit`). Both hyperevm trial proofs send the creation tx by hand. A `--gas` flag or a
   per-chain default would remove that.

## Also for the trial report
trial-hyperlend-hyperevm (placed 21:03Z, attempts:1872) will log burst cases it cannot afford under the 1 USD/tx
trial cap as `opportunity_skip` / `gross_not_above_gas_cap` with their `gross_usd`. On 2026-11-13 the winners of
such cases paid 6-1,100 USD of gas per take (about half the gross). If those skipped rows add up, a variant with a
per-transaction cap of 20-50 USD (inside L, but outside the trial terms) is the question to forward to the human.
