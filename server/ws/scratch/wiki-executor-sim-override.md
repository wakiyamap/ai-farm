---
type: pitfall
chains: [any]
protocols: [aave_v3, morpho_blue, balancer]
---
# Paper-mode executor sims: bake every config into immutables

**Conclusion:** a paper-mode `eth_call` of an executor that is not yet
deployed on mainnet needs a state override with the constructor-linked
runtime code (`eth_getCode` of a fork deployment, not the forge artifact —
the artifact leaves immutable slots as placeholders). Every value the
executor reads from **storage** is zero under that override, so a storage
`owner` makes every sim revert `ONLY_OWNER`. Declare config as `immutable`
(POOL, VAULT, owner) so the baked runtime carries it, and simulate from the
baked owner address.

Evidence (2026-11-03, aave-watcher-arbitrum executor): with only a code
override at 0x14115b5f..., `liquidate()` from the intended owner reverted
`ONLY_OWNER` while `owner` was a storage var; after
`address public immutable owner` the same call reached the Pool and reverted
with the eligibility selector `0x930bb771` for a healthy position — the
correct fail-closed behavior. The live deployment bakes the real owner (the
gate deploys through the bot's wallet at promotion); the bot checks
`owner() == me` on-chain before every send and skips (logs, no gas) on
mismatch. Artifact: `scratch/aave-executor-arbitrum/`, fork evidence in the
bot manifest. Without the override the empty executor address returns `0x`
— a sim that "succeeds" while proving nothing.
