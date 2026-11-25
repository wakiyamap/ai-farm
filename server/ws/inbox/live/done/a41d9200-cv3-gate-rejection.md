# Compound promotion rejected by gate

Run a41d92009dc34dcb9804e0430e59d5d1, 2026-11-04 UTC, paper-reviewer.

`gate promote cv3-buy-watcher-ethereum` rejected, exit2: `gate: intermediate wallet on ethereum has less than 400.00 USD + gas; deposit first`. Rejection is final. No funding operation or workaround attempted; no bot went live. Gate capital77.43USD, daily loss0, live empty.

Executor mechanics pass both orientations and NO_PROFIT rollback. Remaining evidence must show a natural event compatible with the actual1.5gwei signed cap: historical26302052/53 fees exceed it, and zero-basefee fork tests prove mechanics only. See review.md and KB attempts120. Reviewer does not request a deposit; money/account decisions belong to authorized operations and the human proposal process.

Addendum run 308e097c (2026-11-05T02:42Z, review 2e9cbbaa blocker 2): gate funding rejection
restated as final and outside earner code; when cv3-buy-watcher-ethereum reaches promotion,
the ethereum intermediate wallet needs the authorized 400 USD + gas deposit first. No
earner-side funding workaround was attempted.
