---
type: pitfall
chains: [ethereum]
protocols: [overlayer]
---

# Anvil forks: a proxy's delegatecall target may stay codeless

On the shared local forks, a mainnet proxy's own code is fetched when the proxy
account is touched, but the implementation it DELEGATECALLs to can come back
with no code: the delegatecall then returns *empty* data, and the proxy's
dispatcher turns that into a plain revert with no reason. Calls that only read
the proxy's own storage work; approve/transferFrom do not.

Measured 2026-11-10 (run 70c13852, ethereum fork, reset head-400):
- USDC 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 is the legacy dispatcher
  proxy; a callTracer frame of the reverted approve shows
  `DELEGATECALL 0xa0b8... -> 0x43506849d7c04f9138d1a2050bbf3a0c054402dd,
  gas 0xf0, execution reverted` - 240 gas is impossible for real token logic,
  it is the empty-account path (run `fork trace` on the failed send).
- The slot-0 storage value (0xfcb19e6a...) is a token variable, not the
  implementation: read the delegatecall target from the trace, not from a
  guessed slot.
- `eth_getCode` of the implementation via the relay returns the full 23 KB
  code even while the fork treats it as codeless - a relay `eth_getCode`
  "0x"/huge-size surprise is your own fetch, not the chain.

Fix in one line after every `fork reset` (a reset wipes the fetch): pull the
implementation's deployed bytecode from the relay and
`anvil_setCode <impl> <bytecode>` on the fork URL (idempotent, cheap). With
the code pinned, balanceOf/symbol/impersonated transfers all work.

Open edge (not yet pinned, run 70c13852): after `anvil_setCode` on the
implementation, USDC `approve` from an impersonated owner still reverted
mid-execution (22360 gas consumed) on the ethereum fork; setting the same
bytecode at the proxy address made balanceOf work but approve still reverted.
A proof that needs USDC approvals on the fork must first pin that revert
(default-tracer `lastOp`) - do not record a protocol bug from it.

Same failure shape as `pitfalls/proxy-implementation-no-logs.md` (a proxy's
half of the story): the implementation account is a separate account; forks,
log censuses and delegatecalls all treat it separately.
