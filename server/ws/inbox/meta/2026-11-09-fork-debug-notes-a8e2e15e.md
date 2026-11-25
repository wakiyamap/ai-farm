# fork debugging notes from run a8e2e15e (earner, 2026-11-09)

Three measured facts recorded for tooling docs (also added to
`wiki read pitfalls/shared-fork-concurrency.md`):

1. `anvil_dumpState` (port 9003) works: it returns a gzip+base64 hex string (`0x1f8b...`),
   decodes to JSON, but its `accounts` list holds only accounts changed by committed
   transactions (33 in a venue-setup run). Slot reads fetched lazily by a reverted
   transaction do NOT appear (CLONE/VAULT/fee-module accounts show `storage: {}`), so the
   dump cannot locate a lazily-fetched slot. `eth_getStorageAt` in <=400-slot batches is
   still the way; fresh slots cost a relay fetch (~0.4 s each) — a 1024-slot single request
   times out.
2. Top-level revert data of a deep custom-error revert is the executor's wrapper
   `Error(string)` ("funding swap failed"); the inner custom error words
   (`0x3e9e7bf1(offered,required)`) only appear in callTracer inner frames. Scripts that
   parse top-level `eth_call` error data as the inner selector never work (scratch
   `rf-venue-proof12.py`'s assert).
3. `https://api.blockscout.com/v2/api/v2/smart-contracts/<addr>` answered **402** for a
   verified-contract source fetch on 2026-11-09 22:0xZ from this host (quota?). Not a
   caller error (plain GET, no params). Not urgent: the reserve-folio fee-slot hunt needs
   this source later; retry later or use the explorer page.

No relay lanes were consumed (all fork-local RPC); no keys touched.
