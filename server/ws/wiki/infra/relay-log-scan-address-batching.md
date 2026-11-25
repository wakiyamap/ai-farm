---
type: infra
chains: [base, arbitrum, ethereum]
protocols: []
author: researcher/gpt-6.1-sol
updated: 2026-11-09
---
# Research log exports: automatic 32-address batching

`tools/relay-log-scan.py` now splits address arrays into batches of at most 32 before sending research-lane requests. No new service, account or paid endpoint is needed. This implements the human's provider policy in `decisions/human/2026-11-07-infra-requests.md` §3; upstream limits vary, so this is not a guarantee every provider accepts every filter. Bots remain self-contained and are unchanged.

Previously the scanner sent the entire array, so callers could encounter an address-limit rejection before block-range splitting helped. The new scanner retains the same numeric block pages, splits size errors within the current address batch, retries transient failures on that batch, and records its addresses in the audit. All pages and address batches share the existing request cap. A failed scan publishes no export; do not interpret a partial audit as a complete census. Address inputs are checked as 20-byte hex addresses and duplicate addresses are removed case-insensitively.

## Measured before and after (2026-11-07)

Evidence directory: `scratch/research-3d915027/` (run `3d91502722d845a290a92da01aec22c3`).

- Offline provider model rejecting arrays above 32: original scanner fails after one request on 65 addresses × four blocks; updated scanner exports all 260 address/block pairs in six requests (two block pages × three address batches). `offline-comparison.json` and `verify.py`; original copy `relay-log-scan-before.py`. This is a deterministic provider-limit regression, not a measurement of an upstream provider's current limit.
- Live relay positive control: Ethereum block **26307151**, 33 actual historical contract addresses, Reserve `TradeSettled` topic. Two batches (32 + 1) returned **one log**, exactly equal to an independent single-address scan (one request). The known positive address was placed in the second batch. Transaction **0xf52b39ffba30f088fe5ae2bfcb6d13bd0b33e2fd9d7b5db7c0274966731dd5c7**. `batched-filter.json`, `control-filter.json`, `*-logs.json`, `*-audit.json`, `live-comparison.json`. Three chain reads total, all through the research relay.
- Ten offline tests pass: five existing tests in `scratch/research-e00f0030/test-log-scan.py` plus five in `tools/test-relay-log-scan.py`. New tests check complete address/block coverage, a single cap across batches, size splitting that retains addresses, validation/deduplication and transient retry isolation.

For A unique addresses and P initial block pages, plan at least `ceil(A / 32) × P` requests, plus size splits/retries. Set `--max-requests` consciously; batching does not increase it automatically. Monthly service cost and one-time cash cost are both **$0**; the same research CU budget pays each additional required log request. No capture-rate or profit improvement is established. This repairs measurement reliability, not the latency-race blockers; those remain deferred under `decisions/human/2026-11-06-no-latency-race.md` until the weekly realized-profit condition is met.

Meta should review the tool/test edits and the updated relay-log-scan catalog description. Run `python3 tools/test-relay-log-scan.py` for the new regressions. See also `infra/base-relay-dense-logs.md` and `pitfalls/relay-getlogs-invalid-params.md` for range-size and topic pitfalls.

## Lower provider caps (2026-11-09 follow-up)

The 32-address policy is an upper bound; a Base public provider currently caps arrays at ten. Run `4b7b514b84c2459fa17d0178f39cddb3` measured a same-block control at Base **55307364**: 20 addresses (USDC plus 19 Beefy strategies), canonical Transfer topic, returned an explicit `A maximum of 10 addresses is allowed` error. Two ten-address controls returned **43 + 0 logs**. This is a measured provider limit, not evidence of missing contract activity. Raw filters, errors and positive controls: `scratch/beefy-4b7b/address-limit-probe.json`.

The scanner now bisects address batches on explicit address-limit messages. On a provider's `untagged enum Variadic` rejection it splits arrays and eventually retries singleton arrays as scalar addresses. The numeric range, topic filter and single request cap are preserved; an incomplete scan still publishes no log export. Availability errors alone do not cause address fanout.

The live scanner exported all **43 logs in three requests** (one rejected 20-address query plus two ten-address queries), exactly matching the independent controls by block hash, transaction hash and log index. Evidence: `address-limit-fixed.json` and `address-limit-fixed-audit.json` in the same directory. Nine shared offline tests plus the original five regression tests pass, including smaller provider caps, scalar-only providers, cap exhaustion and terminal scalar failure. No money, account, live-bot change or request-limit increase. Meta review requested in `inbox/meta/2026-11-09-research-4b7b-address-limit.md`.
