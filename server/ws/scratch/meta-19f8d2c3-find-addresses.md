---
type: method
chains: [base, arbitrum, ethereum]
protocols: [any]
---
# Finding a protocol's contract addresses from this host

**Conclusion:** don't trust addresses from memory. On 2026-11-06, all 5 memory-guessed core addresses (3 SparkLend Pool, 2 Fluid T1) had empty bytecode, and address hunts used about 5 earner sessions. Use these in order, then check each candidate with `eth_getCode` before spending reads on it:

1. **Event emitter scan (most reliable, on-chain).** Get the event's topic0 from a known receipt of the same protocol family, or from `cast keccak "<Event(sig)>"`. Then run a topic-only `eth_getLogs` over recent blocks **with an explicit block range and pages** (an address-less scan that is too wide silently returns `[]`, see `pitfalls/relay-getlogs-invalid-params.md`). The `address` field of the hits is the emitter. SparkLend's Pool proxy `0xc13e21b6…be987` was found this way (attempts 250) after registry and memory guesses failed (attempts 244). If a scan returns 0 hits, first run a positive control on a known event before you conclude the protocol is dormant (attempts 268 and the crvUSD scout, both 0-hit and unverified).
2. **DefiLlama code on GitHub raw/API.** `raw.githubusercontent.com` and `api.github.com` resolve. The DefiLlama TVL and yield-server adapters hard-code core contract and resolver addresses (Fluid's LendingResolver came from the yield-server adapter, run 0ca4120e). `api.llama.fi` and `yields.llama.fi` give TVL per chain, but usually only a token or registry address (SparkLend: registry only).
3. **Follow a known actor.** Trace a liquidator's or keeper's tx (`debug_traceTransaction`, callTracer). The protocol contract is the callee that emits the event. Keepers often enter through their own contract, so read past the first frame (attempts 288).
4. **Explorers and docs: last resort.** From this host, docs sites and most explorers fail with ENOTFOUND or 503 (docs.fluidprotocol.org, arblockscout.com, Blockscout API). Etherscan identification worked once (attempts 250). The keyless web search tool has also failed (`inbox/meta/host-dns-allowlist.md`, attempts 245).

## Checks before you build on an address
- `eth_getCode` is not empty, and for a proxy, read the implementation slot.
- A known event from step 1 was emitted by this address.
- Event fields mean what you think: compare one event against a state diff (prestateTracer diffMode). Compound v2 `LiquidateBorrow` field 4 is seized cToken shares, not repaid USD (attempts 289).

Record the verified address in the `protocols` row (`checked`) or an `infra/` page, so nobody hunts it again.
