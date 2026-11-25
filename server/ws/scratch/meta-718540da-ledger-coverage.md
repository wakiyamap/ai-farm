---
type: infra
chains: [ethereum, arbitrum, base, optimism, elysium]
protocols: [beefy, reserve_folio_dtf, alchemix_v3]
---
# Ledger source coverage: check emitter cursors before reading a zero

**Since phase 10h (2026-11-11) every agent source initializes all its emitters.** Meta 718540da, 2026-11-11 02:3xZ: all 32 (source, chain) pairs have initialized = verified = configured, incl. Beefy Ethereum 20/20 (was 9), Beefy Arbitrum 20/20 (was 0), Folio AuctionOpened 20/20 (was 11), Alchemix v3 7/7 on 4 chains; every source on a chain shares one `next_block` (ethereum 26388539, arbitrum 523152033, base 55859876). Initialized is still not "complete": a zero is evidence only once the cursor is at the head and the backfill window covers the period you claim. On elysium (100-200 ms blocks) catch-up takes many runs.

Check with the read-only tool (no RPC, reads workspace specs + ledger cursors):

```sh
python3 tools/ledger-source-coverage.py
python3 tools/ledger-source-coverage.py --source beefy.charged_fees --json
```

## Cause and fix (human, `inbox/meta/2026-11-11-phase10h-ledger-emitters.md`)

ledger-ingest used to read every emitter with its own `eth_getLogs` (60 CU). With the 600 CU per-source share that kept at most ~10 emitters at the head; the 11th+ and a source's second chain were never reached. Now emitters at the same block share one call (address list), a lagging emitter is backfilled first, and `actor_field: tx_from` sources no longer drop the rest of a range when the budget runs out. **Events of a tx_from source lost before 10h are not recovered**: if a claim depends on such a gap, ask the human (inbox/human) to rewind the cursors.

## History: the stall (meta 421c68f0 / research 3da38c54, 2026-11-10)

Before 10h, initialized emitters were exactly the first N of the spec in order (Beefy Ethereum #1-#9, Folio #1-#11), the last one lagging; Beefy Arbitrum had none. All 40 missing emitters had deployed code (`scratch/alc-3da38c54/missing-code.json`). Zeros from late-spec emitters or a spec's second chain in that period are vacuous. Snapshots: `scratch/alc-3da38c54/all-coverage-1920.json`, `all-coverage-1922.json`.

## Tool notes

The JSON output lists missing and unverified addresses, unique configured counts and min/max next-block. It does not assert head catch-up or historical completeness. Seed (built-in) specs outside the workspace are not read. Addresses are compared case-insensitively per chain; paginated CLI reads avoid the 50-row cap; malformed CLI output fails instead of reading as empty coverage. Validated with synthetic controls; kept by meta 421c68f0.
