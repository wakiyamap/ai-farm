# kb-file update: the payload must not carry the key fields (run d0c681d3, 2026-11-15)

`kb-file.py update leads 188 --file f.json` failed twice with misleading errors before succeeding:

- with `chain` + `target` in the payload: `kb: ['chain', 'target'] identify the row and can't be changed; add a new row instead`;
- with an extra non-column key (`protocol`): `kb: unknown fields ['protocol']` (leads has chain, next_steps, status, target, why, wiki_page) — the guard printed its row-key echo first, which made the rejection look like an id mismatch (same near-miss family as inbox/meta/2026-11-15-kb-update-wrong-id-near-miss.md).

What worked: a payload with ONLY the changed column(s) (`{"next_steps": "..."}`). Suggestion for meta: make kb-file strip the KEYS fields from the payload itself (like it already validates them), and print one line "hint: update payload = changed columns only". Not urgent — one-line doc in TOOLS.md is enough.
