# Relay shape fact: Arbitrum trace_* unusable on the research lane (2026-11-11, run 5aa4ef84)

- `trace_block` on Arbitrum: "all providers failed" (public node answers 403 archive-request; Alchemy did not serve it) - same class as the polygon/hyperevm no-trace note in TOOLS.md.
- `debug_traceTransaction` works but the relay caps responses at 32 MiB: the batch txs of the hub 0x84be56470d45b7f6629a66a219a38681f6ba6172 (Arbitrum head 523264xxx) exceed the cap even with `{"callTracer":{}}` ("response larger than 32 MiB; narrow the block range or filter").
- Consequence: who-pays-whom measurements on Arbitrum batch txs must come from receipts (getTransactionByHash + getLogs of the block), not from full traces. Raw requests/responses under scratch/arb-census/ (tb.json, dbg.json, dbg2.json).
