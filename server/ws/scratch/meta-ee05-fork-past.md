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
Since phase 15c (11-18) the fork has its own `fork` lane (400k CU, Alchemy first; 600k by 11-19).

**Fixed in the relay for forks (phase 15h, 2026-11-19 ~05:40Z), except once the fork budget is spent:** a fork-lane
state read pinned to a block older than ~800 blocks goes to Alchemy only (even while Alchemy is cooling down); a
rate limit comes back as JSON-RPC 429, which anvil retries. Cause before 15h: one cooldown per upstream URL shared by
all lanes, so another lane's timeout pushed the fork's old-state read to a public node (`missing trie node`,
`no provider available`). Research and scout lanes are unchanged: keep one retry on an RPC error in research
scripts and treat `missing trie node` there as "retry later", not a revert.

**Fork lane budget spent = no old-block fork for the rest of the UTC day (2026-11-19, 4 sessions):** the decision
said old-state fork reads use Alchemy even after the budget is spent; in practice they did not. Relay `/health`
showed `fork` 601,490 of 600,000 CU at 09:43Z, and from then until at least 14:46Z every `fork reset arbitrum <block
hours to 5 days old>` failed with `all providers failed: public: HTTP 403 Archive requests require a personal token`
(builder runs 7790a143, 05728037, 996fcff1, cb0420ed; reviewer b0031010). Base resets mostly still worked, one
`fork deploy` in three hit the same 403 and passed on retry. Forwarded to the human (meta ee059752).
- How to tell: the 403 text above on a fork call, and `fork` at or over its budget in `/health`.
- What still works: `fork reset <chain> <block 5-20 minutes old>` (builder f4111558, three times on arbitrum), so
  deploy, owner and guard reverts can be real fork txs; the success at the old block either waits for 00:00Z or is
  an archive `eth_call` through the research lane with the fork deployment's runtime as a code override
  (`scratch/trial-gmx-buyback-slow-arbitrum/proof_head.py`). Write in `fork_evidence` which part is still owed.
- Otherwise pick relay-only work for the session instead of retrying.

## How to tell (research lane on public nodes)
- `python3 tools/rpc.py <chain> eth_getLogs ...` (research lane) answers
  `all providers failed: public: HTTP 403 ... Archive requests require a personal token`.
- On the fork, `eth_call` fails with `failed to get account for 0x...` or `failed to get storage for 0x... at ...`.
  Retrying the same call gets further each time (anvil keeps what it fetched): 3-30 retries for a Fluid quote on
  arbitrum (`scratch/trial-fluid-arbitrum/probe_fork.py`).
- A view that works on the relay at that block reverts on the fork. HyperLend
  `getUserAccountData` at hyperevm block 51273260: fine through the relay (paper lane), `panic 0x11` on the fork with
  the right block timestamp. Likely cause (not verified slot by slot): a public node answered a past-block storage
  read with newer state, so `block.timestamp - lastUpdateTimestamp` underflows.

## bsc: `missing trie node` on a 4-day-old fork (2026-11-19, before 15h)
- builder-claude run c6a6f716, reset bsc to 133,621,097 (~4 days old), fork lane at 111k CU (fresh):
  `cast call` failed `failed to get storage for 0x0f3aDA81... : -32000: missing trie node`, the identical call
  succeeded seconds later; earlier `fork send` gave `no receipt ... after 30s`, then `no provider available`, and
  `fork status` showed `bsc down` until `fork lease` + `fork reset`. The research lane served the same slot fine.
  Cause: the shared cooldown above (bsc-dataseed keeps recent state only). Fixed by 15h for the fork lane.
- Effect: a proof script that treats any failed `eth_call` as "reverts" reports a false "no route". **Retry each
  simulation once on an RPC error (`-32000`, `missing trie node`, `failed to get storage`) and count only a real
  revert as a revert**; reviewers re-running a proof should do the same.
- Cost: 18 historical simulations per run, two failed runs = ~110k fork-lane CU in minutes.
- bsc public nodes on the research/scout lane also answer a historical `eth_call` with the **latest** state, no
  error (scout a25fa579, 11-19: `depositId()` at five blocks back to 0x3000000 all equal to head). A flat historical
  read on bsc is no evidence unless a control at the same blocks varies.

## arbitrum: `public: HTTP 403 Archive` on the fork after 15h (2026-11-19 08:12Z)
- paper-reviewer run 57f67367, `fork reset arbitrum 525390726`, then a proof `probe()` failed loading PEAS storage
  with the 403. First guessed as the ~800-block threshold; the later sessions above show the fork budget was the
  cause (spent shortly after).

## What still works
- An `eth_call` at a past block through `tools/rpc.py` (research lane, Alchemy while its budget lasts) with the
  executor as a **code override** (third parameter `{"0xexec": {"code": "0x..."}}`) runs the whole flash-loan
  path and returns the gain; `eth_estimateGas` takes the same override. The runtime is the artifact's
  `deployedBytecode` with the immutable owner written at `immutableReferences`
  (`scratch/trial-hyperlend/selftest.py`). Builders must not use `--lane paper` for their own reads (15c).
- `fork reset <chain>` with no block (head) gave consistent state. For a lending liquidation you can make the case
  on the fork: a funded address supplies, borrows the maximum, withdraws collateral down to HF 1.00003, then
  `evm_increaseTime` 6 h at a time until interest puts HF under 1 (12 h on HyperLend). Success, healthy revert,
  NoProfit revert and nothing-left revert all come out of one script (`scratch/trial-hyperlend/proof_head.py`).
- Keep the past-block proof script next to it so the reviewer can run it after the UTC day rolls.

## HyperEVM extras
- `fork deploy` fails with `intrinsic gas too high -- tx.gas_limit > env.block.gas_limit`: send the creation tx by
  hand (`fork send` without `to`, data = artifact bytecode + constructor args, gas 1,900,000).
- Past blocks report `gasLimit` 3,000,000 on the fork, but the gate and signer still refuse more than 2,000,000.
