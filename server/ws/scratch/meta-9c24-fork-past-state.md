---
type: pitfall
chains: [any]
protocols: [hyperlend, fluid_lending]
---
# A past-block fork was not trustworthy when its lane fell back to public nodes (fixed for the fork, 11-20)

**Current state (phase 15i, human 2026-11-20):** every fork-lane read goes to **Alchemy only, whatever the block,
with no daily cap**. Public nodes are never used by a fork, so an old-block `fork reset` works at any hour and
"fork budget spent" no longer exists (the 95,200,000 shown for `fork` in `/health` is the month, not a cap). A fork
call can still fail on Alchemy itself (429, which anvil retries, or an Alchemy error). **If `public:` appears in a
fork error after 15i, write time (UTC), chain and block in `inbox/meta/`.** The sections below are the history and
still apply to the **research and scout lanes**, which do fall back to public nodes once their budget is spent
(research 1.5M, scout 1.2M CU/day since 11-20).

**Conclusion (2026-11-17, builder-claude run ab638f11):** the shared fork read through the research lane. Once
that lane is over its daily Alchemy budget it falls back to public nodes, and a fork at a past block then either
fails read by read or, worse, answers with inconsistent state. Since phase 15c (11-18) the fork has its own `fork`
lane.

**Phase 15h (2026-11-19 ~05:40Z) did not work as described:** it sent a fork read to Alchemy only when the relay's
`is_historical()` called the block old, which it did not for anvil's reads. Within the budget a fork read went
Alchemy, then public (Alchemy cooling down -> `public: HTTP 403 Archive`, the 08:12Z arbitrum case); past the budget
public only. Research and scout lanes are unchanged: keep one retry on an RPC error in research scripts and treat
`missing trie node` there as "retry later", not a revert.

**History: fork lane budget spent (2026-11-19, 4 sessions, before 15i):** relay `/health` showed `fork` 601,490 of
600,000 CU at 09:43Z, and from then until at least 14:46Z every `fork reset arbitrum <block hours to 5 days old>`
failed with `all providers failed: public: HTTP 403 Archive requests require a personal token` (builder runs
7790a143, 05728037, 996fcff1, cb0420ed; reviewer b0031010). Reset to a block 5-20 minutes old still worked (builder
f4111558). Forwarded to the human (meta ee059752), answered by 15i.

## How to tell (research / scout lane on public nodes)
- `python3 tools/rpc.py <chain> eth_getLogs ...` answers
  `all providers failed: public: HTTP 403 ... Archive requests require a personal token`.
- On a fork before 15i, `eth_call` failed with `failed to get account for 0x...` or `failed to get storage for 0x...
  at ...`; retrying got further each time (`scratch/trial-fluid-arbitrum/probe_fork.py`).
- A view that works on the relay at that block reverted on the fork: HyperLend `getUserAccountData` at hyperevm block
  51273260, `panic 0x11` on the fork. Likely cause (not verified slot by slot): a public node answered a past-block
  storage read with newer state, so `block.timestamp - lastUpdateTimestamp` underflows.

## bsc: `missing trie node` on a 4-day-old fork (2026-11-19, before 15h)
- builder-claude run c6a6f716, reset bsc to 133,621,097 (~4 days old): `cast call` failed `missing trie node`, the
  identical call succeeded seconds later. Cause: a shared upstream cooldown sent the read to bsc-dataseed (recent
  state only).
- Effect: a proof script that treats any failed `eth_call` as "reverts" reports a false "no route". **Retry each
  simulation once on an RPC error (`-32000`, `missing trie node`, `failed to get storage`) and count only a real
  revert as a revert**; reviewers re-running a proof should do the same.
- bsc public nodes on the research/scout lane also answer a historical `eth_call` with the **latest** state, no
  error (scout a25fa579, 11-19). A flat historical read on bsc is no evidence unless a control at the same blocks
  varies. On 11-19 ~16:58-17:10Z bsc state reads (`eth_getCode`, `eth_call`, `eth_getBalance`, `eth_getStorageAt`)
  returned empty for every address on every lane, WBNB included, while headers, receipts and logs worked (scout
  39530aba): a bsc `eth_getCode` of `0x` counts only with a non-empty WBNB control in the same run.

## What still works on the research lane
- An `eth_call` at a past block through `tools/rpc.py` with the executor as a **code override** (third parameter
  `{"0xexec": {"code": "0x..."}}`) runs the whole flash-loan path and returns the gain; `eth_estimateGas` takes the
  same override. The runtime is the artifact's `deployedBytecode` with the immutable owner written at
  `immutableReferences` (`scratch/trial-hyperlend/selftest.py`). Builders must not use `--lane paper` for their own
  reads (15c).
- Lending liquidation at head: a funded address supplies, borrows the maximum, withdraws collateral down to HF
  1.00003, then `evm_increaseTime` 6 h at a time until HF < 1 (`scratch/trial-hyperlend/proof_head.py`).

## HyperEVM extras
- `fork deploy` fails with `intrinsic gas too high -- tx.gas_limit > env.block.gas_limit`: send the creation tx by
  hand (`fork send` without `to`, data = artifact bytecode + constructor args, gas 1,900,000).
- Past blocks report `gasLimit` 3,000,000 on the fork, but the gate and signer still refuse more than 2,000,000.
