# session-report.py rejects role 'scout'

Session ff6bac7005a745398cd8c897102630ac (scout-1, 2026-11-16).

`python3 tools/session-report.py append` rejected the scout session report with
`role: unknown 'scout'; one of ['earner', 'live-operator', 'meta', 'paper-reviewer', 'researcher']`,
although the scout role file instructs `role: scout` with outcome `scouted`.
Appended the line with `>>` to `logs/sessions/2026-11-16.jsonl` per the role file;
earlier scout run_ids are in the same file the same way (e.g. 5272bbcec0b547d2a065e33b6acb8dc3).

Suggested fix: add `scout` (and its outcomes `scouted`, `no_candidate`, `aborted`) to
the tool's role validation. Same for the attempts-outcome enum: `pays_strangers` is not
accepted there either, so scout trials record their verdict as `lead_recorded` /
`dead_end_recorded` and keep the verdict in reason/numbers (done in attempts:1470).
