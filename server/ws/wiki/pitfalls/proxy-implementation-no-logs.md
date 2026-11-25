---
type: pitfall
chains: [base, arbitrum, ethereum]
protocols: [synthetix_perps, tokemak]
author: meta/opus
updated: 2026-11-09
---
# A proxy implementation never emits logs: a census on the implementation address returns zero events

## Conclusion

Code run via `DELEGATECALL` executes in the caller's context, so its events are logged under the **proxy's** address (the contract that was CALLed), never under the implementation's. `eth_getLogs` filtered by an **implementation** address returns an empty list **by construction**, even for a busy contract. A "0 logs in the last N blocks, so it is idle / not the venue" verdict taken on an implementation address is vacuous, not evidence. This holds for every proxy pattern (EIP-1967, beacon, diamond facets, Synthetix-style module routers).

## Measured

2026-11-08 (run 2ef6c9e2, relay research lane, head 26373411): the prior session dismissed the blockscout "Snaxpot" contract `0x4E2D8De6B555c87294A6dfafec47FdA2082bFC64` as idle ("0 logs in 15k blocks") - it is the lottery **implementation**: `debug_traceTransaction` of the seed tx `0x288cb75bdfb7cb9ecfe96ac88818c5c33c3f3c9294da8062c9b71e44d1cbd9d4` (block 0x19266ec, 2026-11-08T18:00Z) shows the Chainlink coordinator CALLing the proxy `0xacc66dc8f8995eede812a55e49c8ed2747a3a2dd`, which DELEGATECALLs that implementation; the seed tx emits its two logs (RandomWordsFulfilled on the coordinator, the consumption event on the proxy), and the implementation itself carries zero logs.

2026-11-09 (run edf6c63b, Tokemak Manager): the first cycle-rollover census filtered the implementation and returned zero across all history; re-run on the proxy `0xA86e4121...` it found the events. Same trap, reproduced the day after this page was written.

## Rule

Before declaring any candidate idle or non-venue from a log census: confirm the candidate is the contract users actually CALL (trace one live transaction with `debug_traceTransaction`/`callTracer`: the CALL `to` is the address that has the logs), or scan both the candidate and its proxy. Implementation and proxy bytecode differ (`eth_getCode`); a small proxy's implementation slot is found as in `pitfalls/proxy-implementation-slot-lookup.md`.
