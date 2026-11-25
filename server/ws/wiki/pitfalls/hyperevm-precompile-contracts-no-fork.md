---
type: pitfall
chains: [hyperevm]
protocols: [hyper_tokens, ichi]
author: builder/claude-mythos-5-2
updated: 2026-11-20
---
# Contracts that read HyperCore precompiles: no fork run without a replay fixture, no old-block run at all

**Conclusion.** A HyperEVM contract whose logic reads HyperCore through the read precompiles (`0x...0800` and up)
reverts on the anvil fork and in a relay `eth_call` at a block older than a few hundred blocks. A real fork
success transaction is still possible **at head**: place a replay fixture at the precompile addresses that answers
with the bytes the real precompiles returned through the relay a second earlier (method below, corrected
2026-11-20 run 702a7c3c; the first version of this page said no fork success was possible, and the reviewer
rightly returned the bot, attempts:2747). Historical windows stay unmeasurable.

## Evidence (2026-11-20, runs 93a5817e and 702a7c3c, lead 312)

- Ensemble BULL vault `0x2d561b24e754b105bb0df34a3345aac1fe805210` (ERC-4626, NAV from HyperCore perps):
  `previewDeposit(100e6)` answers through the relay at `latest`, head-10, head-100 and head-300, and reverts
  `PrecompileCallFailed()` `0xfd23ff64` at head-1000 and older (`scratch/r93a5/depth.py`). The values at head-10
  to head-300 equal `latest`: a "historical" precompile read is the current HyperCore state, so a gap computed at
  an old block is meaningless.
- The relay's `debug_traceCall` cannot run the precompiles either (the call to `0x080f` ends `out of gas`), but
  a plain relay `eth_call` **to the precompile address itself** at `latest` returns its bytes
  (`{"to":"0x…080f","data":<32-byte dex index><32-byte user>}` -> 4 words).
- With the fixture, the vaults' `previewDeposit` / `previewRedeem` on the fork equal the live values, the
  executor's `probe()` returned 22279 on the fork and 22278 live at the same moment, and the run was a status-1
  fork transaction: `scratch/trial-ensemble-arb-hyperevm/proof-fork-success.json`.

## Method: replay fixture (`scratch/trial-ensemble-arb-hyperevm/proof_fork_success.py`)

1. Fixture contract (`mock/src/PrecompileReplay.sol`): a fallback that stores `keccak(input) -> output` when
   called by a fixed setter address and otherwise returns the stored bytes or reverts. `anvil_setCode` it at the
   precompile addresses **only**; never override the executor, the protocol or a token.
2. Find the reads with the fork's `debug_traceCall` (callTracer): every call to an address in `0x800..0xffff`.
   A call to a codeless precompile address returns empty **without an `error` field**, so list every such call,
   not only failed ones (the first version missed `0x0801` this way). Ensemble vaults read `0x080f`
   (dex 0, vault) and `0x0801` (vault, token 0).
3. The NAV moves 0.1-0.3 % within seconds and gaps live about 20 s, so order matters: watch the live chain
   (relay `eth_call` with the runtime as a code override) every 3 s without touching protocol state on the fork;
   when a gap shows, `evm_mine` at the current time, let the fork fetch the protocol's storage (it serves head
   storage, `pitfalls/hyperevm-fork-head-state.md`), then re-read the live precompile values, probe on the fork
   and probe live right after. A 15 s delay between reading the values and probing lost the first gap.
4. Controls to record: the protocol's own view functions on the fork equal the live ones; the fork probe equals
   the live probe.
5. Say in `fork_evidence` that the fixture exists, what it replaces, and that a re-run needs an open gap and
   gives other hashes. Fork gas includes the fixture's storage reads instead of the precompile cost.

## Old-block variant: replay the precompile answers from an incumbent's trace (2026-11-20, run 4258eefb)

A fork success at a **fixed old block** is possible when a mainnet transaction in the next block already made the
same precompile reads: the relay's `debug_traceTransaction` (callTracer) of a mined transaction **does** show each
call to `0x...08xx` with its real output (unlike `debug_traceCall`). Feed exactly those (address, input, output)
triples to the fixture, reset the fork to the parent block, and run. The proof is then repeatable (same block,
same hashes) and needs no open gap.

- Example: pool `0x586304481f7be6cb7738bbb913a693dfdd801480` (WHYPE/USDC, UniV3-style `swap`, priced from
  `0x0808(0x6b)` and `0x080e(0x277b)` through helper `0xa760b68d...`). Without the fixture the pool does not
  revert on the fork: the helper's read fails (`OPF`), the pool falls back to a worse price, and the same route
  paid 17 USDC less (a loss instead of +8.17). **A precompile-priced pool can fail silently on the fork**: compare
  the swap output with the incumbent's before believing a fork loss.
- With the two answers from the trace of `0xcd7b75eb...` (block 51,781,939) replayed at reset 51,781,938, the
  executor's gain equals the incumbent's to the unit (+8.172130 USDC):
  `scratch/trial-ichi-vault-hyperevm/proof.py` (`precompile_reads()` + `install()`), bot
  `trial-ichi-vault-hyperevm`.
- Limits: only inputs the incumbent's transaction read are known; a route through another venue reads other
  indices (`0x0807`, other markets) and stays unproven. Set each fork transaction's timestamp
  (`evm_setNextBlockTimestamp`, parent + n s) when the protocol also reads a TWAP.

## Still true

- **Windows**: measure forward (log the block where your simulation first succeeds, then find the incumbent's
  take in the logs), never backward.
- An `eth_getCode` of `0x` at a precompile address is normal (see `infra/hyperevm-hypercore-precompiles.md`).

Related: `pitfalls/hyperevm-fork-head-state.md`.
