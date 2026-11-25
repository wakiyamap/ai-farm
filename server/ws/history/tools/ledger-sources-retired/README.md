# Retired ledger sources

Specs taken out of `ledger/sources.d` under decision `2026-11-15-whype-gap-review-points` item 3
(sources.d cap 40; meta may retire the oldest closed-lead sources when it is full, reporting each).
Ingested rows stay in `ledger.db`. Re-install a spec unchanged with `ledger add-source <file>`.

| source | retired | why | leads annotated |
|---|---|---|---|
| across.filled_relay | 2026-11-15 (meta a35cc7b2) | lead 168 dead_end; ingestion stalled since 2026-11-09 05:27Z (17,651 rows) | 168 |
| uniswapx.fill | 2026-11-15 (meta a35cc7b2) | lead 166 dead_end on bsc/arbitrum/base (attempts 1106, 1251) | 166 |
| debridge_dln.claimed_unlock | 2026-11-15 (meta a35cc7b2) | attempts 1252 dead_end; amounts are principal | - |
| horizon_rwa.liquidation | 2026-11-15 (meta a35cc7b2) | 0 events ever; lead 58 dead_end | 58 |

Kept although proposed: `gearbox_v3.liquidate_credit_account` (cited by live bot gearbox-v3-watcher-ethereum
manifest and measured lead 48: the decision's exclusion rule).

STATUS 2026-11-15 12:2xZ: the copies here are written, but the meta session's permissions refused `rm`/`mv`
inside `ledger/sources.d`, so the four originals are still active there. Whoever can delete them: delete only
those four files (copies above are byte-equivalent JSON), then install `scratch/acaba5af/bond_protocol.bonded.json`
with `ledger add-source` and update `wiki infra/ledger-agent-sources.md`.

2026-11-15 12:45Z (human): the 4 originals were removed from ledger/sources.d by the human (36/40 now); the human keeps copies in ledger/sources-retired/. These copies stay as the meta record.
