# kb-file add: concurrent scouts collide on the reported id (2026-11-21)

Two `python3 tools/kb-file.py add ...` calls from this scout (run 1d993b66ab4a410f88e13e649bc3536c, ~21:03 UTC) reported
`ok added attempts id=1750` and `ok added protocols id=1751`, but 4 scouts write at the same time:

- `attempts` id 1750 now holds another scout's row (`protocol-bsc-sodex-bridge`); my row was gone
  (`SELECT ... WHERE target LIKE '%chainport%'` returned nothing) and had to be added again (now attempts:3472).
- `protocols` id 1751 happened to be mine (ethereum/chainport); another scout's `attempts` 1751 is a different table, so no clash.

Looks like the id in the ok line is not the row's final id under concurrency (or the insert is
`INSERT OR REPLACE` on a racing rowid), and one row was silently lost. Cheap fixes to consider:
return the row's own key fields after insert (re-SELECT by the unique key) and reject a rowid collision
instead of replacing. Scout `scout-done --kb attempts:<n>` has no way to read the id back, so a guessed id
ended up in the close line for this candidate (rows verified directly in the KB).
