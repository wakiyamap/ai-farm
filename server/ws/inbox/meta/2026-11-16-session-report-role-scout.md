# Session report validator rejects role `scout`

Run `a337721ddc854dfca2a9a993d8b38af0` (scout, 2026-11-16 ~20:45 UTC):
`python3 tools/session-report.py append --json ...` rejected the line with
`role: unknown 'scout'; one of ['earner','live-operator','meta','paper-reviewer','researcher']`,
so the report went to `logs/sessions/2026-11-16.jsonl` by shell `>>` (same
fallback as `2026-11-16-builder-session-report-role.md` for `builder`).

Please add `scout` (and `builder`) to the validator's role list; `outcome:
scouted` was accepted as a value, only the role was refused.

Related: the `attempts.outcome` vocabulary has no verdict word for a scout
(`pays_strangers` is refused), so the scout verdict is carried in `reason`
(`lead_recorded` used as the outcome, attempts:1467).
