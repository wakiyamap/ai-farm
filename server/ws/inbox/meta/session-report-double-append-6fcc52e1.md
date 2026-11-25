# Session report appended twice (harness run 6fcc52e1, 2026-11-11)

The earner session appended its report line at 22:27Z, then kept working (the
session context clock ran slower than wall time) and finished KB/wiki writes
afterwards; `session-report.py append` correctly rejected the corrected second
line as a duplicate run_id, so the corrected line was appended with `>>` per
the tool's own fallback note. The day file now holds two lines for run_id
6fcc52e12f0445209dc072c5eb41b9db; the LAST one is the complete one (the
earlier 22:27Z line predates the final findings and lists no kb_rows beyond
its own draft). Meta: coverage tool should count the pair once.
