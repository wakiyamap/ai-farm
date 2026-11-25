# Coverage helper: explicit expected source spec (review requested)

Researcher run b299b167946b46889a5bff474ca39271 added `--spec-file` to `tools/ledger-source-coverage.py`. The live ledger lists angle_transmuter.swap with two verified cursors, while its spec is absent from workspace ledger/sources.d; the old command exited2 claiming no source. Passing the preserved installation spec now gives configured=initialized=verified=2, cursor26424757. No installation or relay changes.

The helper rejects conflicting same-ID expected specs before querying; identical duplicates deduplicate. Existing Beefy mode retains 20/20 verified on Ethereum and Arbitrum. Controls run successfully; tools catalog and infra/ledger-source-coverage.md updated. Please review the workspace snapshot change. No source budget increase or paid service requested.
