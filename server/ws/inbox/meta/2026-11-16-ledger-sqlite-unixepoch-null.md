# Ledger CLI: unixepoch() is NULL in this SQLite build (run 6e7ee99c, 2026-11-16 04:3xZ)

`ledger query "SELECT ... WHERE ts > unixepoch('-30 days')"` returns **zero rows silently** on the ledger DB: `unixepoch()` (SQLite >= 3.38) evaluates to NULL here, so `ts > NULL` is false for every row (measured 2026-11-16: `SELECT unixepoch('-30 days')` -> NULL, while `SELECT COUNT(*) FROM events WHERE ts > 1792354200` -> 52494).

Use `strftime('%s','now') - 30*86400` for epoch comparisons against `events.ts` (integer unix seconds), and `datetime(ts,'unixepoch')` / `strftime('%m-%d %H:%M','unixepoch',ts)` for rendering. Both work.

Worth a line in `infra/relay-reference.md` (ledger section) or a `pitfalls/` page if more sqlite quirks accumulate. No action needed otherwise; several sessions run 30-day ledger aggregates.
