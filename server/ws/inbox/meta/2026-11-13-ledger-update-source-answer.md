# ledger update-source: not now (human, 2026-11-13)

- No new command for now. The extra concentrator emitter is harmless (one more address in a getLogs call), so the source stays as it is.
- If a source is wrong in a way that loses or corrupts events, write it to inbox/human with the corrected spec path; the human replaces that one file by hand.
- If this comes up for a third source, ask again and the command will be built.
