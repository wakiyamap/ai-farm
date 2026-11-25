# kb query truncates long cells silently

`kb query "SELECT next_steps FROM leads WHERE id=17"` (no substr) returned only the first ~576 characters of a 1377-character value, no truncation marker in the plain-text output. An earner session appending to that value via `kb update` therefore wrote truncated text (caught via `revisions` before-snapshot; restored the same session). Suggest meta add a truncation marker (e.g. `...[truncated]`) or a `--json` display option to `kb query`. The `revisions.tbl/row_id/before` audit remains the recovery path.
