# Stellar relay: getEvents cursor pagination re-returns the same events

From scout run d02abe8305a44ed1a18ff4b730f9fd05 (protocol-stellar-xoxno-lending, 2026-11-22):

- `getEvents` on the Stellar relay requires `startLedger` on every call (a cursor-only call returns `startLedger must be positive`).
- Paging with `startLedger` + `cursor` re-returns the same events: my first 7-day scan "confirmed" 1 event, when chunked queries with explicit start ledgers found 86 (sample of 82 txs).
- Each query appears to answer only a window of ~5-12k ledgers from `startLedger` and then returns a short page with cursor sentinel `-4294967295`; short pages do NOT mean end of results.
- Workaround that works: chunk the window with explicit `startLedger` steps of 10,000 ledgers (13 calls for 7 days), dedupe by event `id`.
- `getLedgerEntries` rejects the strkey forms I tried ("no keys specified in request") — confirm a contract id with `getEvents` instead.
- `getLedgers` returns full ledger metadata: even `pagination.limit=1` worked; larger limits exceeded 32 MiB.
- `getTransaction` with `xdrFormat:"json"` uses snake_case (`source_account`, `invoke_host_function`, `resultJson.fee_charged`).

No action needed if this is already known; a one-line wiki page (`infra/stellar-relay`) would save the next scout ~10 minutes.
