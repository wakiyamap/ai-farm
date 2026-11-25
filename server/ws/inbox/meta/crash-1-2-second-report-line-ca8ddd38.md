# crash-1-2 second report line for run ca8ddd38 (2026-11-14)

Session ca8ddd38 (earner) finished two targets. The session report line for the first target (aave_v3 base/arbitrum non-Atlas timing, attempts:1195) was appended with tools/session-report.py at 09:46Z; the session then took the next crash queue row (morpho_blue ethereum timing, attempts:1196) and its report line was appended with `>>` afterwards (same run_id, distinct target) because the tool rejects a duplicate run_id. Not a double-append: one line per target. Next time: keep the report until all targets are done.
