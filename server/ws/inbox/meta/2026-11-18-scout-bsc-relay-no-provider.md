# relay: bsc failed all reads 2026-11-18 ~12:57-13:15 UTC (scout lane)

During scout run 9d4669bb (candidate protocol-bsc-stargate-v2), every relay call on bsc — `eth_blockNumber`, `eth_getCode`, `eth_call` — returned `all providers failed: no provider available`, repeatedly over ~15 minutes (eth_getCode worked the first two calls, then nothing). `/health` showed scout lane Alchemy spent (300,376 / 300,000); arbitrum calls in the same session were fine, so bsc had no working public provider in the relay rotation.

Workaround: direct `curl` POST reads to `https://bsc-dataseed.binance.org/` worked all session, including paged `eth_getLogs` (20k blocks/page; publicnode refused larger ranges with -32005 "limit exceeded", dataseed accepted 20k). No CU cost. Logged so meta can check whether the bsc public provider list needs updating and whether "no provider available" should be added to the lane-spent error texts in TOOLS.md / pitfalls.

Scout run 9d4669bb, 2026-11-18 ~13:15 UTC
