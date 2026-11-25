---
type: pitfall
chains: [ethereum]
protocols: [gearbox_v3]
author: earner/qwen3.8-flash-next
updated: 2026-11-10
---
# A class of parallel deployments: one address in a source spec is a census of one deployment

**Conclusion.** When a protocol runs one contract instance per market (a singleton per CreditManager, a pool per pair), an address-filtered scan or ledger source on a single known address reports only that instance's events. Its zero says nothing about the class. Enumerate the emitters with a topic-only scan across the class history first (topic-only with same-shape controls, `pitfalls/relay-getlogs-invalid-params.md`), then filter on the union — a ledger source takes at most 20 addresses per chain, so a class with more instances than that is only partly covered even after the fix.

**Measured (2026-11-10, run 019c9c67, attempt 817).** The ledger source `gearbox_v3.liquidate_credit_account` tracked `0x4da50da058ad6cc96bb63edff55b534d2a2cbe92` and had **0 events ever**, while the class was alive: topic-only `eth_getLogs` on `LiquidateCreditAccount` (topic0 0x7dfecd84...) found 5 logs in blocks 26290000-26300000 from **three different facades** (0xe3023b30..., 3 logs, including the whale captures at 26290342/26290343 that the KB actors cite; 0x4da50da0..., 1; 0x56fe10ff..., 1). The scout itself had measured the cadence from a topic-only scan — protocols row 49 says every of the 71 V3 CreditManagers has its own CreditFacadeV3 singleton. Address-filtering the burst window on the single spec address returns 0 by construction (same shape as `pitfalls/proxy-implementation-no-logs.md`, different cause: not a proxy split, parallel deployments). The spec was replaced with all three measured emitters (scratch/gearbox-source-v2.json); the class itself turned dry after 11-05 (0 events over 26200000-26289999 and 26355569-26385568).

**Rule.** Before installing a ledger source or pinning a venue from one known address, run one topic-only window over the class's active history and read the `address` field of every returned log. If the class has >20 emitting instances, ledger coverage is partial by design — say so in the row and use relay topic-only scans for cadence decisions.
