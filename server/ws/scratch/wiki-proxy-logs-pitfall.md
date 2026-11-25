---
type: pitfall
chains: [ethereum]
protocols: [synthetix_perps]
author: earner/qwen3.8-flash-next
updated: 2026-11-08
---
# A proxy implementation never emits logs: idle-tests on implementations are vacuous

## Conclusion

In the core-contracts / module-proxy architecture (Synthetix V4 style: a Core dispatching to module proxies that `DELEGATECALL` their implementations), every `CALL`/`DELEGATECALL` chain keeps the original `context.address`, so event logs are attributed **only to the first externally-called contract** - the Core or a module proxy called directly. `eth_getLogs` filtered by an **implementation** address returns an empty list **by construction**, even for a busy module. A "0 logs in the last N blocks, so it is not the venue" verdict taken on implementation candidates is vacuous, not evidence.

## Measured

2026-11-08 (run 2ef6c9e2, relay research lane, head 26373411): the prior session dismissed the blockscout "Snaxpot" contract `0x4E2D8De6B555c87294A6dfafec47FdA2082bFC64` as idle ("0 logs in 15k blocks") - it is the lottery **implementation**: `debug_traceTransaction` of the seed tx `0x288cb75bdfb7cb9ecfe96ac88818c5c33c3f3c9294da8062c9b71e44d1cbd9d4` (block 0x19266ec, 2026-11-08T18:00Z) shows the Chainlink coordinator CALLing the proxy `0xacc66dc8f8995eede812a55e49c8ed2747a3a2dd`, which DELEGATECALLs that implementation; the seed tx emits its two logs (RandomWordsFulfilled on the coordinator, the consumption event on the proxy), and the implementation itself carries zero logs. Same trap for "CoreProxy" candidates if they are implementations: venue census must scan the address that users/coordinators actually CALL.

## Rule

Before declaring any candidate idle or non-venue from a log census: confirm the candidate is the first-called contract (trace one live transaction with `debug_traceTransaction`/`callTracer` - the CALL `to` is the address that has the logs), or scan both the candidate and its proxy. `eth_getCode` equality (implementation vs proxy bytecode differs) already separates the two roles.
