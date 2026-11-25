---
type: infra
chains: [ethereum, arbitrum, base, optimism]
protocols: [beefy, reserve_folio_dtf, alchemix_v3]
---
# Ledger source coverage: installed specifications can have missing emitter cursors

An `active` source is not proof that all configured emitters are tracked. Check each configured chain/address against `cursors` before interpreting event zeros or describing class-wide coverage. The free read-only audit tool `tools/ledger-source-coverage.py` compares workspace agent source specifications with the public ledger CLI. It never queries the database file or chain RPC directly.

```sh
python3 tools/ledger-source-coverage.py
python3 tools/ledger-source-coverage.py --source beefy.charged_fees --json
```

## Pattern: initialization stops in spec order (meta 421c68f0, 2026-11-10 20:3xZ)

In both partial sources the initialized emitters are **exactly the first N addresses of the spec, in order**, and the last initialized one lags behind the rest: Beefy Ethereum = spec #1-#9, #9 (`0xE577...`) at next_block 26382675 while #1-#8 sit at 26386714; Folio AuctionOpened = spec #1-#11, #11 (`0x9f45...`) at 26378040 while #1-#10 sit at 26386714. Beefy Arbitrum (the second chain in the spec) has none. So the ingest daemon apparently initializes emitters one at a time and stalls on one (still backfilling, or failing every tick on the next one). Reported to the human: `inbox/human/2026-11-10-meta-ledger-emitter-init-stall.md`. Until fixed, **a zero from an emitter late in a spec, or on a spec's second chain, is not evidence of no events**: put the addresses you care most about first, or scan them with `relay-log-scan`.

The JSON output includes missing and unverified addresses, unique configured counts, initialized/verified counts, and the min/max next-block cursor. It does **not** assert catch-up to head or historical completeness: those require a head and an explicit backfill start. Seed specifications outside the workspace are deliberately not read. Case-insensitive addresses and separate chains are handled independently. Bounded CLI pagination avoids the ledger's 50-row result cap; malformed CLI output fails instead of being interpreted as empty coverage.

## Measurement after the phase 9e fairness change

Research run `3da38c54c60b470bad7bb50fc657ee8a`, 2026-11-10 **19:19–19:22 UTC**, follows the first Beefy install from 2026-11-09 around 19:20 and its explicit recorded next step. No earnings census was repeated. Source snapshots and results are in `scratch/alc-3da38c54/all-coverage-1920.json` and `all-coverage-1922.json`.

| Existing source | Configured | Initialized / verified after tick 710 |
|---|---:|---:|
| Beefy Ethereum | 20 | **9 / 9** |
| Beefy Arbitrum | 20 | **0 / 0** |
| Reserve Folio AuctionOpened Ethereum | 20 | **11 / 11** |

All **31 missing Beefy emitters and 9 missing Folio emitters have nonempty deployed code** at explicit current block tags (`missing-code.json`); this eliminates absent contracts as the explanation for these particular missing cursors. It does not establish their correct event ABI or activity.

Tick 710 ran 19:21:20–19:21:49, reported `cu_agent=6020`, and left Beefy's initialized count unchanged at 9/40. Its minimum/maximum next_block remained **26380675 / 26386481**. Folio's count remained 11/20 while its min/max advanced **26372040/26386481 → 26374040/26386558**. This is incomplete emitter initialization about 24 hours after the Beefy install, not evidence that its other 31 strategies have no rewards. Meta's 20:3xZ re-check: unchanged counts (Beefy 9/40, Folio 11/20).

New source `alchemix_v3.position_claimed` became active at 19:21:20 and obtained its first verified Ethereum cursor. At 20:3xZ it had both Ethereum emitters (2/2) and 0 of 5 on arbitrum/base/optimism; check again after subsequent ticks.

Validation of the new audit tool: synthetic controls covered address case/deduplication, a missing emitter and the same address on another chain; live output matched independently issued aggregate cursor queries. Meta 421c68f0 ran it and kept it.
