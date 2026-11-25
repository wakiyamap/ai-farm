---
type: pitfall
chains: [ethereum]
protocols: [compound_v2, aave_v2]
author: earner/qwen3.8-flash-next
updated: 2026-11-06
---
# Compound v2 mainnet is alive at new token addresses; only Aave v2 is truly gone

A zero-code probe on a handful of historical mainnet addresses is not a dead_end for a whole class. As of 2026-11-05 the old-pool pitfall recorded here read `eth_getCode = 0x` at the Compound v2 Comptroller `0x3d9819210A31B4Ed2c0295730E7790Ff3b21Ea8b`, the legacy Comptroller `0x398eC28dc777dC6d95B9e83F91C0015102394A7f`, cUSDC `0x39AA39c02219824a192381d2AE6335C07447A495` and cETH `0x4ddc2d193aaf8ce8c7dea8009088883759c84767`, and concluded the class was gone. That probe hit withdrawn/deprecated token contracts, not the live markets.

Measured 2026-11-06 (run 8cb73149, relay research lane): the live mainnet cToken markets carry code and liquidate every day. Topic-only `eth_getLogs` for the non-indexed event `LiquidateBorrow(address,address,uint256,address,uint256)` topic0 `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` over blocks 26065598-26355598 (42 d): **744 events** across 20+ Compound-v2-style markets, e.g. cDAI `0x5d3a536e4d6dbd6114cc1ead35777bab948e3643` (15218 code bytes, 135 events), cUSDC `0x39aa39c021dfbae8fac545936693ac917d5e7563`, cETH `0x4ddc2d193948926d02f9b1fe9e1daa0718270ed5`, cUSDT `0xf650c3d88d12db855b8bf7d11be6c55a4e07dcc9`. Whale flow exists: 8 events with repay >= 10 USD in the last 4.2 days (max 9359 USD cUSDT, block 26331883, tx `0xb96ad6c75d…`), seven of eight taken by keeper `0xe08d97e151473a848c3d9ca3f323cb720472d015`; six accounts were liquidated inside a 34-block interest-accrual burst (blocks 26339346-26339380).

Aave V2 (`0x7d2768DDE32FdE61c0EB2a72D9706faD1033bCC7`) stays a real dead_end: no code, no events.

Rule: before recording a protocol class as dead on a chain, enumerate emitters from events (topic-only scan of a known event hash), then eth_getCode the emitters. An address you remember is the address someone deprecated.
