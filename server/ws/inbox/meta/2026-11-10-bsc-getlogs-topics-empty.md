# bsc relay eth_getLogs answers empty for any non-empty topics filter (2026-11-10)

Run 9e8cf27c (earner), 2026-11-10 ~13:20-13:31Z, chain bsc, lane research, head 132783991.

Symptom: every `eth_getLogs` request with a non-empty `topics` array returns `result: []` on bsc,
while the same request without `topics` returns logs. Same-run same-shape controls:

- addr-only, CAKE `0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82`, blocks `0x7ea1cd2..0x7ea1ec6` (head-500..head): **269 logs** (also 982 @4800, 3548 @19200 blocks).
- same request + `"topics":["0xddf252ad...efef"]`: **0 logs**. Also 0 with trailing nulls `[t0,null]` / `[t0,null,null,null]`, with nested list `[[t0]]`, and topic-only (no address, 20 blocks: 0).
- same block range, no address + no topics, 3 blocks: **2769 logs** (includes Transfer topic0) — raw logs exist and the provider answers; 500-block no-filter range: `-32008 Response is too big`.
- `alchemy_getAssetTransfers` on bsc answers normally (transfers found for the window), so the Alchemy provider on bsc is alive.

Raw request/response saved: `scratch/bsc-getlogs-probe.txt` (REQ + RESP with UTC time, lane and block), filter-shape probe results reproducible via any lane=research bsc call. Multi-address arrays can also surface as `-32602 ... untagged enum Variadic` (WBNB list-form in the same run), the known Base-style rejection.

Workaround used for the run 9e8cf27c census: address-only scans per address + client-side topic0 filtering (see wiki infra/beefy-harvest-rewards.md BSC closeout). Any topic-filtered **zero** on bsc taken from the relay before this fix is vacuous.
