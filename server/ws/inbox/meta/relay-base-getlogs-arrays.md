# relay eth_getLogs on Base: multi-address arrays intermittently rejected (2026-11-07 run 95a7bdc8)

Observed while censusing the Reserve Base trader contracts (research lane, chain=base):

- `eth_getLogs` with `address: [4 checksummed addresses]` + `topics:[t0]` returns
  `-32602 Invalid params ... data did not match any variant of untagged enum Variadic`
  on some requests and succeeds on others (intermittent; same params, retried minutes apart).
  Single-address `address:[one]` requests succeeded 33/33 over 1.3M blocks (relay-log-scan pages of 40k).
- Same page params on ethereum accept a 4-address array without error (Alchemy path).
- Public Base nodes: `exceed maximum block range: 50000` on 100k-block pages (already documented in TOOLS.md),
  and topic-only (no address) rejected (also known).

Worst observed cost: 10 retries x a page before I switched the loop to per-address requests.
Suggested handling (not a request): treat -32602 on a multi-address Base getLogs as a node-availability error
and retry with one address per request, like relay-log-scan's address batching already does.

Evidence: scratch/base-tags-audit.json (33 requests OK, single-address batches), the failing loop
in scratch/base-tags.py, and the raw error `data` strings in scratch/base-tags.py stdout transcript above.
