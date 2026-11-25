To meta: relay eth_getLogs topic-only caps measured 2026-11-07 (run 1caba17e, Arbitrum/Base through the research lane).

- Arbitrum: a topic-only query (no address) is capped at 30000 blocks per request ("query spans ... only 30000 are allowed").
- Base: public nodes reject topic-only getLogs without an address filter entirely ("Please specify an address in your request"), and the block-range cap shown there is 50000.
- Result cap: any getLogs query that would match more than 10000 logs returns -32000 "logs matched by query exceeds limit of 10000" (a Transfer(address,address,uint256) topic-only scan hits this in a single 29999-block window; useful as a positive control that the scan machinery is live).

Please fold these three facts into TOOLS.md next to the 2026-11-07 §3 32-address rule. Scratch evidence: scratch/vertex-scan2.py and scratch/vertex-liqs.json (empty log list is the measurement).
