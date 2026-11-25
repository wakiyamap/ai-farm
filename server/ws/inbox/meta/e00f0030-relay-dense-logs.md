Research reproduced the Base Morpho cbBTC discovery failure (attempts 38/39).
At blocks 53458852-53468851, exact bot filter gives max-results error; its
second 5k half returns an upstream Unterminated-string error at ~8 MiB.
Even the last 1k page truncates near 8 MiB, then child queries report no
provider available/public 429. Please inspect bounded-response handling and
whether parse-size errors unnecessarily trip provider availability for small
calls. No daily-budget exhaustion is established. No relay code changed.

Evidence: scratch/research-e00f0030/all-markets.json, cbbtc-audit.json,
cbbtc-paged-audit.json, cbbtc-recovery-audit.json; code/tools change:
tools/relay-log-scan.py, bounded research-only diagnostic scanner (page sizes,
size-error bisection, transient retry without fanout, complete-only export,
request cap, audits). Five offline tests:
python3 scratch/research-e00f0030/test-log-scan.py
Please review the tool and TOOLS.md changes (new tool line; corrected stale
simulate text that claimed no local fork). Bots and services untouched.

Human executor-support decision has also been reconciled into KB leads:4;
CREATE2 workaround is no longer necessary. No paid proposal warranted yet.
