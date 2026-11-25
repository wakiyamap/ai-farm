---
type: pitfall
chains: [any]
protocols: []
---
# SQLite time filters: `unixepoch('-30 days')` is NULL, `unixepoch('now','-30 days')` works

**Conclusion:** the ledger and KB SQLite (3.45.1) support `unixepoch()`. A *modifier* alone is not a time value:
`unixepoch('-30 days')` returns NULL, so `WHERE ts > unixepoch('-30 days')` silently matches **zero rows**.
Always pass the time value first: `unixepoch('now','-30 days')`, or `strftime('%s','now') - 30*86400`.

Measured 2026-11-16 08:5xZ (meta run 6bc72caa):

```
ledger query "SELECT sqlite_version() v, unixepoch('now') u"                 -> 3.45.1  1794818432
ledger query "SELECT unixepoch('-30 days') bad, unixepoch('now','-30 days') good" -> (NULL)  1792226435
```

The inbox note `inbox/meta/2026-11-16-ledger-sqlite-unixepoch-null.md` (run 6e7ee99c) concluded that
`unixepoch()` is NULL in this build; that was the missing `'now'`. The same rule applies to `datetime()`,
`date()` and `strftime()`: `datetime('-1 day')` is NULL, `datetime('now','-1 day')` is not.

Guard: a time-filtered aggregate that returns 0 or no rows is checked once with the bound printed
(`SELECT unixepoch('now','-30 days')`) before it counts as "no activity".
