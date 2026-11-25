---
type: pitfall
chains: [any]
protocols: [aave_v3, morpho_blue, compound_v3, moonwell, balancer]
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

Related: `pitfalls/paper-review-blockers.md`, `pitfalls/executor-fork-gotchas.md`.
