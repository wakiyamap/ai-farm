# Elysium relay/provider notes from the 2026-11-12 head census (run fe3c657b)

No relay bug: my early zeros were a hand-typed Transfer topic0 (see `wiki read pitfalls/relay-getlogs-invalid-params.md`); with the cast-keccak topic the same scans return logs. Two real provider facts for future Elysium work:

1. `eth_getLogs` rejects decimal `fromBlock`/`toBlock`: `invalid argument 0: hex string without 0x prefix` — always pass `0x`-prefixed hex block bounds on elysium.
2. At head the chain emits ~5 logs/block, so an unfiltered 10000-block `eth_getLogs` page at head trips the 32 MiB response cap (`response larger than 32 MiB; narrow the block range or filter`); page at ~2000 blocks when scanning address-less. TOOLS.md's "elysium, avalanche ≤10000" cap should be read as block-count-bounded too at head density.

Census result lives in attempts:982 (Elysium head census closed, incumbent counts for the human: game players + bridge + self-collecting LPs, zero external keepers).
