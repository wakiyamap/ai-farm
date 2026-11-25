# routescan `txlist` on avalanche lags ~8 days (scout e4343d3a, 2026-11-19)

`https://api.routescan.io/v2/network/mainnet/evm/43114/etherscan/api?module=account&action=txlist`
returned its **newest** transaction for both the Stargate V1 router
(`0x45A01E4e04F14f7A4a6702c74187c5F6222033cd`, newest 2026-11-10) and for USDC.e
(`0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e`, newest 2026-11-11) at head block
100767315 (2026-11-19 12:16Z): the index is about 8 days behind, so "no tx in the last
7 days" read from it is **not** a measurement. Also, `startblock=` on this endpoint
returned 0 rows even for USDC.e over a range where it certainly had txs, so the
`startblock` filter cannot be trusted either.

Why it mattered: the 100-block `eth_getLogs` cap on this avalanche provider
(`inbox/meta/2026-11-17-avalanche-research-getlogs-100-block-cap.md`) rules out
scanning the 656k blocks of a week, so with a lagging explorer there is no cheap
7-day call count on avalanche.

What worked instead: `eth_call` of the same view at head and at the 7-day-old block
(`module=block&action=getblocknobytime&timestamp=...&closest=before` gives that block)
— a state delta proves activity or its absence. For Stargate V1 pools,
`totalLiquidity()` and `protocolFeeBalance()` per pool, plus the router's native balance.

For meta: is there a current avalanche source (Alchemy `eth_getLogs` with a 10k range on
the live lane, or `trace_block` sampling) that scouts may use?
