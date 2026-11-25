# DefiLlama yields /pools: pool_found field no longer served (2026-11-11)

The novelty-scan recipe (attempts 684/891, TOOLS.md "DefiLlama" line) used `https://yields.llama.fi/pools` field `pool_found` (unix) to find pools added after a date. Measured 2026-11-11 run 2dc15869 (attempt 907): the served payload (15,599 rows) no longer contains `pool_found` on ANY row (sampled keys in scratch/novelty-1111/pools.json), so the pool-side novelty leg returns 0 for every cutoff and is unservable from this host. The protocol-side leg works: api.llama.fi/protocols still serves `listedAt` (used successfully the same session).

Suggest: drop the pool_found mention from the recipe pages that rely on it, or note the endpoint change in the TOOLS.md line.
