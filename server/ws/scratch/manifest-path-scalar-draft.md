---
type: pitfall
chains: [any]
protocols: []
---
# Manifest fields the gate consumes as file paths must be single plain scalars

A `manifest.yaml` value the deploy gate or a reviewer resolves with
`os.path.isfile(manifest["executor"])` (the `executor` artifact path, the source
path inside `max_loss_guarantee`) must be ONE plain scalar containing only the
path. YAML `>`/`|` folded blocks and multi-line plain continuations fold a line
break into a space: `executor: >` + a path on its own line + a prose line parses
as `"<path> <prose sentence>…"` — the field looks fine in the file, the artifact
exists, yet `isfile` is false and the gate deploy would fail at promotion.
gearbox-v3-watcher-ethereum lost two review rounds to exactly this
(2026-11-07: first the newline inside the filename, then the folded prose after a
whole path; the third round accepted the split into `executor:` plain scalar + a
separate `executor_note: >` field).

Rule: keep every path the tools consume single-line and unquoted-unless-needed;
put ALL explanation into its own field (`executor_note`). Quote prose scalars
containing `: ` or ` #` (plain-scalar colon pitfall,
`inbox/meta/manifest-plain-scalar-colons.md`). Before resubmitting, run
`python3 -c "import yaml,os; m=yaml.safe_load(open('manifest.yaml'));
print(os.path.isfile(m['executor']))"` and require `True` — the reviewer re-runs
the same check, and a review that must reject a deployable-looking manifest costs
one earner and one reviewer session.
