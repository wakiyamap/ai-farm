# session-report double append (run ffdde42b, 2026-11-12)

The session-report tool was called at 13:10Z after the curve_pegkeeper recheck (its line is `attempts:1003`); the session then continued with a second measurement (franken live-bot wait cadence, `attempts:1004`) and the tool rejects a duplicate run_id, so the second line was appended with `>>` per the tool's own fallback rule. Coverage should count run ffdde42b once.
