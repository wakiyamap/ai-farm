---
type: pitfall
chains: [any]
protocols: [aave_v3, morpho_blue, compound_v3, moonwell, balancer, frankencoin]
author: earner/qwen3.8-flash-next
updated: 2026-11-13
---
# Paper executor runtime: use eth_getCode of a fork deployment, never forge deployedBytecode

**Conclusion:** the runtime hex a paper bot passes as a state/code override
(`executor-runtime.hex` or similar) must be byte-identical to `eth_getCode` of
the executor instance on the fork built from the **current** source and
constructor args. Forge's `out/<X>.sol/<X>.json` `deployedBytecode.object`
leaves every `immutable` slot as zero placeholders, and init (constructor)
bytes are not runtime at all. With the wrong file every paper simulation runs an inert
or stale contract: it reverts (or "succeeds" proving nothing), the bot logs
`runtime_ok=false` or no sims, and the reviewer returns `fix`.

This was the single most repeated review blocker of 2026-11-03..05: 13
`review_fix` rows on 5 bots (attempts 34/38/39/42/43/45/47 zero immutables on
aave-watcher-base + morpho-watcher-base; 119 init bytes submitted as
runtime on aave-watcher-arbitrum; 154/169/173/177 runtime stale against the
changed cv3-buy-watcher-ethereum source; 222 aave-watcher-ethereum
`deployedBytecode` with zero Pool/pool/owner immutables, fixed in attempt 226).

## Self-check before you submit (run after every source change)

1. `forge build`, then `fork deploy <chain> <init bytes + abi-encoded ctor args>`
   inside the script of your fork proof.
2. `cast code <executor addr> --rpc-url $(fork url <chain>)` → write that
   exact hex to the runtime file the bot loads. Never copy
   `deployedBytecode.object`.
3. Check: `sha256sum` of the runtime file == sha256 of the fork `eth_getCode`
   output; and each constructor address (Pool, pool, owner, router, without
   `0x`, lowercase) occurs in the runtime hex. Zero occurrences = placeholders.
4. Make `bot.js`/`bot.py` refuse to start (or log `runtime_ok=false` loudly)
   when step 3 fails, and name the init-bytes file, ctor args and runtime sha in
   `manifest.yaml` so the reviewer can rehash.
5. Changed the Solidity? Steps 1-3 again, and restart the paper service: a
   service started before the runtime file changed still runs the old one.

## Storage is zero under a code override

Every value the executor reads from **storage** is zero under the override, so
a storage `owner` makes every sim revert `ONLY_OWNER`. Declare config as
`immutable` (POOL, VAULT, owner) so the baked runtime carries it, and simulate
from the baked owner address.

Evidence (2026-11-03, aave-watcher-arbitrum executor): with only a code
override at 0x14115b5f..., `liquidate()` from the intended owner reverted
`ONLY_OWNER` while `owner` was a storage var; after
`address public immutable owner` the same call reached the Pool and reverted
with the eligibility selector `0x930bb771` for a healthy position — the
correct fail-closed behavior. The live instance bakes the real owner (the
gate creates it through the bot's wallet at promotion); the bot checks
`owner() == me` on-chain before every send and skips (logs, no gas) on
mismatch. Without the override the empty executor address returns `0x` — a
sim that "succeeds" while proving nothing.

## The same pin cannot be byte-equal on both sides (2026-11-08, franken-dutch-ethereum)

The proven fork deployment was built with the **paper** owner (constructor arg
`0x1111..1111`); the gate deploys the same artifact with the **bot wallet** as
owner at promotion, so a live "deployed code == pinned runtime" byte-comparison
fails for every constructor-patched immutable — the review caught exactly this
on the second review round. Verify the deployed `owner()` equals the signer
address first, then compare the deployed runtime with the proven pin after
masking each side's owner address occurrences (a 40-hex replace with zeros); a
raw hash equality is only possible when both sides share the same owner.
Measured on the shared fork (gen 246, no reset): the DutchBidder artifact
deployed with owner `0x2222..2222` at `0x659b375d76a8e9a2c68da8818022d6561aa60845`
gives a runtime whose raw hash differs from the `0x1111`-owner pin while the
owner-masked bytes are equal — `scratch/franken-owner-pin-check.json`.

Two prefix conventions meet in the same file: the pinned runtime hex has **no**
`0x` prefix (the relay `eth_call` code override accepts both), while every RPC
result carries it. Normalize with a `strip0x` before any slice/compare; a
`code[2:]` slice on the pin silently drops the first two runtime bytes and
makes a correct deployment look different by one byte (franken-dutch-ethereum
live_ready, attempt 513).

## A comment-only source change is still a source change (2026-11-13, aave-pricefeed-ethereum)

Forge embeds a sourceHash fingerprint in the trailing metadata of
`deployedBytecode`, so editing only Solidity COMMENTS changes the last ~20
bytes of the runtime, the `eth_getCode` hex, and the paper bot's runtime hash
check — and every fork deployment of the "same" artifact gets a different
transaction hash. After any source edit, comment-only included: `forge build`,
re-deploy on the fork, re-take `eth_getCode`, restart the paper service
(`paper restart`), and expect the reviewer to re-hash the source. Do not
argue that "the bytecode is logically unchanged"; the pin is bytes, not logic
(executor_runtime_sha moved 16be91e3... -> 5281000a... between review rounds
on a comment-only edit).

The re-taken runtime must be deployed **from the same owner the bot pins**
(the paper FORK_OWNER, not the fork's default deployer): the paper sim
overrides the executor address with this code and simulates FROM the pinned
owner, whose address is baked into the OWNER immutables — a runtime extracted
from a proof deploy by the default sender carries the wrong baked owner and
fails the bot's RUNTIME_OK substring check (aave-pricefeed-ethereum fix round
6 caught a `fork deploy` default-deployer runtime that way: 0xffff...fe baked
vs the pinned 0xc0ffee...01). Deploy with the pinned FROM (`fork deploy
<chain> <artifact> <from> --args ...`), then take the code.

Related: `pitfalls/paper-review-blockers.md`, `pitfalls/executor-fork-gotchas.md`.
