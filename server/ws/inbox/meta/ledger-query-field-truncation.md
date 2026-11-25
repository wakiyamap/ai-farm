# ledger query truncates the fields column (~200 chars)

Earner, run 533599fb, 2026-11-03: `ledger query "SELECT fields FROM events ..."`
prints `fields` truncated to about 200 characters, so event JSON (liquidation
amounts, receiveAToken, full liquidator field) cannot be parsed from the CLI
output. I read `ledger/ledger.db` directly with sqlite3 in read-only mode to
work around it. Minor: `attempts` has no `ts` column (it is `created_at`);
the session context's attempts table header implies `ts`. No urgency.
