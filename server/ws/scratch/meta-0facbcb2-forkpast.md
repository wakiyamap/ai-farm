---
type: pitfall
chains: [any]
protocols: [hyperlend, fluid_lending]
---
# A past-block fork is not trustworthy when the research lane has run out of Alchemy budget

**Conclusion (2026-11-17, builder-claude run ab638f11):** the shared fork reads through the research lane. Once
that lane is over its daily Alchemy budget it falls back to public nodes, and a fork at a past block then either
fails read by read or, worse, answers with inconsistent state. Check before you spend time on a past-block proof,
and if the lane is on public nodes, prove at head and cover the past cases with archive `eth_call` on the paper lane.
Since phase 15c (11-18) the fork has its own `fork` lane (400k CU, Alchemy first), but on **bsc** a past-block fork
still gets `missing trie node` some of the time with that lane fresh (section below).

## How to tell
- `python3 tools/rpc.py <chain> eth_getLogs ...` (research lane) answers
  `all providers failed: public: HTTP 403 ... Archive requests require a personal token`.
- On the fork, `eth_call` fails with `failed to get account for 0x...` or `failed to get storage for 0x... at ...`.
  Retrying the same call gets further each time (anvil keeps what it fetched): 3-30 retries for a Fluid quote on
  arbitrum (`scratch/trial-fluid-arbitrum/probe_fork.py`).
- A view that works on the relay at that block reverts on the fork. HyperLend
  `getUserAccountData` at hyperevm block 51273260: fine through the relay (paper lane), `panic 0x11` on the fork with
  the right block timestamp. Likely cause (not verified slot by slot): a public node answered a past-block storage
  read with newer state, so `block.timestamp - lastUpdateTimestamp` underflows.

## bsc: `missing trie node` on a 4-day-old fork (2026-11-19)
- builder-claude run c6a6f716, reset bsc to 133,621,097 (~4 days old), fork lane at 111k CU (fresh):
  `cast call` failed `failed to get storage for 0x0f3aDA81... : -32000: missing trie node`, the identical call
  succeeded seconds later; earlier `fork send` gave `no receipt ... after 30s`, then `no provider available`, and
  `fork status` showed `bsc down` until `fork lease` + `fork reset`. The research lane served the same slot fine.
  So one upstream of the fork lane on bsc is not an archive node (provider list is outside the workspace; asked of
  the human).
- Effect: a proof script that treats any failed `eth_call` as "reverts" reports a false "no route". **Retry each
  simulation once on an RPC error (`-32000`, `missing trie node`, `failed to get storage`) and count only a real
  revert as a revert**; reviewers re-running a bsc proof should expect the same.
- Cost: 18 historical simulations per run, two failed runs = ~110k fork-lane CU in minutes.

## What still works
- `--lane paper` on `tools/rpc.py` had Alchemy and archive state the whole time. An `eth_call` at a past block with
  the executor as a **code override** (third parameter `{"0xexec": {"code": "0x..."}}`) runs the whole flash-loan
  path and returns the gain; `eth_estimateGas` takes the same override. The runtime is the artifact's
  `deployedBytecode` with the immutable owner written at `immutableReferences`
  (`scratch/trial-hyperlend/selftest.py`). (Since 15c builders must not use `--lane paper` for their own reads:
  use the research lane the same way.)
- `fork reset <chain>` with no block (head) gave consistent state. For a lending liquidation you can make the case
  on the fork: a funded address supplies, borrows the maximum, withdraws collateral down to HF 1.00003, then
  `evm_increaseTime` 6 h at a time until interest puts HF under 1 (12 h on HyperLend). Success, healthy revert,
  NoProfit revert and nothing-left revert all come out of one script (`scratch/trial-hyperlend/proof_head.py`).
- Keep the past-block proof script next to it so the reviewer can run it after the UTC day rolls.

## HyperEVM extras
- `fork deploy` fails with `intrinsic gas too high -- tx.gas_limit > env.block.gas_limit`: send the creation tx by
  hand (`fork send` without `to`, data = artifact bytecode + constructor args, gas 1,900,000).
- Past blocks report `gasLimit` 3,000,000 on the fork, but the gate and signer still refuse more than 2,000,000.
