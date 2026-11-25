---
type: pitfall
chains: [base, arbitrum, ethereum]
protocols: [any]
author: meta/opus
updated: 2026-11-07
---
# The shared local fork: lease it briefly, check the generation, and old anchors may return empty state

Conclusion: the anvil forks (`fork status`, ports 9001-9003) are **shared by every
session**. Since phase 6k (2026-11-05) take a lease before measuring:
`fork lease <chain> <minutes ≤60> [note]` makes other runs' `fork reset` / `fork replay`
fail (they can override with `--force`, which they must note), and `fork release <chain>`
frees it early. `fork status` shows the lease and a **generation number** that goes up by
one on every reset; `send` / `deploy` / `replay` print it too. If the generation changed
between the start and end of your measurement, the measurement is invalid. A fork
result still counts as evidence only if **one sequential script** does reset -> deploy ->
fund -> guard tx -> success tx and re-checks generation, head and executor code around
every send.

**Keep leases short.** The ethereum fork reached generation 54 on 2026-11-05 and 6 of 10
reviewer verdicts in attempts 153-173 say they could not re-run the earner's proof because
another run held the lease. Without that re-run no bot can be promoted. Lease only while
your script runs, release right after, and never hold a lease while reading or writing.

## Recipe (do this every time)

1. Write the whole proof as one script first. Then `fork lease <chain> 15 "<bot> proof"`; `fork reset <chain> [block]`; record the generation from `fork status` and `eth_blockNumber` as `anchor`.
2. In the same script: deploy (`fork deploy <chain> <artifact.json|hex> --args <abi-encoded constructor args>`), fund, then `evm_snapshot`.
3. Before each send, require the same generation, `eth_blockNumber` >= anchor (and equal to what your
   own sends produced) and `eth_getCode(executor)` == the expected runtime. Abort on mismatch.
4. Guard (NO_PROFIT) tx -> `evm_revert` to the snapshot -> success tx. Record block
   numbers and the generation before and after each tx in the evidence JSON.
5. Treat any timeout, unexpected head or generation change as "contaminated": rerun the whole script, do not stitch results together.
6. `fork release <chain>` as soon as the script exits (put it in a `trap ... EXIT`). Name the script in `fork_evidence` so the reviewer can rerun it.

Reviewers: if the fork is leased, `fork status` shows the seconds left. Review other bots
and retry; do not end the session with "lease blocked" while the lease is about to expire.

## Reported failure modes

| Symptom | Cause / workaround | Source |
|---|---|---|
| **Creation deploy mines status 0, gasUsed ≈ intrinsic creation gas (e.g. 63022), empty revert data, same at head and old resets, same from any sender** | **constructor arguments missing**: solc's constructor reads its args from the end of the code (`61xxxx3803806... ` with `0xxxxx` = file length) and the ABI-decode length check reverts empty. `forge test` passed only because `new X(addr)` appends them. Since phase 6u `fork deploy` warns about this, takes a forge artifact directly and accepts `--args $(cast abi-encode 'constructor(address)' 0x..)`. Do **not** "prove" with `anvil_setCode` of forge's runtime: the constructor never runs and immutables stay zero | decisions/human/2026-11-07-fork-deploy-meta-bash.md (runs de13d8f2, aed4765b, c8bcce4f) |
| `fork reset` / `replay` refused: leased by another run | wait out the lease (`fork status` shows seconds left) and work on something else meanwhile; `--force` only with a note | attempts 153-173 |
| Probe reads head 26328589 right after your reset to 26302052 | another session reset the fork (now: lease first, compare generation) | inbox/meta review b44cbd98 |
| `fork deploy` / `eth_sendTransaction` time out at 9003 | fork busy fetching relay state, or jammed pool; rerun, do not use partial results | review 9328b6b6 |
| Contract has no code / `eth_getStorageAt` returns 0x / `getTransactionCount` hangs / `missing trie node` at an old anchor | the fork lazily fetches state from the relay at the anchor block; public nodes keep only ~1000 blocks of state. Since phase 6k state reads older than head−800 try Alchemy first, so `fork reset <chain> <old block>` should work again; if it still fails (arbitrum still failed ~14k blocks deep on 2026-11-05), use a recent block | inbox/meta relay-historical-state-depth, decisions/human/2026-11-05-capital-fork-git.md |
| `anvil_reset ... historical state <root> is not available` for ~10 min, then the same reset works | transient relay state-cache eviction; retry later, do something else meanwhile | run b4c50493 |
| Pending sends never mine on ethereum / `maxFeePerGas` rejected | after `fork reset` the base fee is mainnet's next block; call `anvil_setNextBlockBaseFeePerGas` before low-fee sends and say so (that proves mechanics, not historical includability) — **and after every later reset inside the same script**, incl. a mid-script guard-phase reset: one injection at script start does not survive it (run d237253f's guard send died on "max fee per gas less than block base fee" exactly there) | run 154fb2fe, run 23f0395f, review a41d9200, run 18dfd4b5 |
| `fork deploy` crashes "File name too long" | it takes a **file path** (hex file or forge artifact), not inline hex | run 23f0395f |
| `fork send` with creation data and no `to` returns status 1 and a contractAddress, but `eth_getCode` is 0x | `fork send` is not a deploy path; use `fork deploy <chain> <file>` | run b4c50493 |
| Raw `eth_sendTransaction` to the fork URL returns `null` | raw sends are filtered; use `fork send` / `fork deploy` | run b4c50493 |
| Creation deploy mines status 0 with a non-empty revert or a gasUsed well above intrinsic | a real constructor revert: read the revert data / callTracer error that `fork deploy` prints (phase 6u). Placing a runtime with `anvil_setCode` is acceptable only for a runtime taken by `eth_getCode` from a real deployment (immutables filled), never forge's `deployedBytecode` | run 23f0395f, run 8b738b25, run b4c50493 |
| Multicall3 `tryAggregate` reports inner failures that single `eth_call`s don't | fork state fetch inside multicall; verify with single calls | run 154fb2fe |
| `fork fund-token` USDC only ~18e6 wei transferable | fund-token moves real tokens from the `<holder>` you name; pick a holder whose balance at the anchor covers the amount and check `balanceOf` afterwards | run 7c5937a3 |
| Your fork state vanished without anyone calling `reset` | **`fork replay` re-forks at the tx's block-1**, which wipes the shared fork like a reset | `fork --help` |
| No receipt right after a send / `fork replay` | the fork mines on an interval; poll `eth_getTransactionReceipt` (~1 s) | pitfalls/executor-fork-gotchas.md, run 23f0395f |
| A **paper-mode bot** on a shared fork never simulates / sim silently skipped | the `paper@.service` unit exports only `RPC_RELAY_URL`/`RPC_LANE`/`BOT_MODE` — **no fork URL**; a bot that reads `FORK_URL_<CHAIN>` from the environment gets `""` and every fork call fails. Hardcode the local daemon (`http://127.0.0.1:9001/2/3` = base/arbitrum/ethereum, from `fork url <chain>`) as fallback. reserve-folio-dtf-ethereum run 5367bc1b |
| A paper simulation of a **currently open** auction reverts as if the auction did not exist | the shared fork sits where the last session reset it (hours-to-days behind the live head; `fork status` shows `fork <block>` vs `mainnet <block>`); a live auction is not on the fork at all. A bot may not hold long leases: lease 1 min, `fork reset <chain> <head-1>`, deploy+fund+eth_call, `fork release` in the same seconds-long window; if the lease is busy, skip that poll and retry next. reserve-folio-dtf-ethereum run 5367bc1b |

None of these mean mainnet semantics differ: the chains are real; the fork tooling is what misbehaves.
