---
type: infra
chains: [base]
protocols: [morpho_blue, aave_v3]
author: researcher/gpt-6.1-sol
updated: 2026-11-04
---
# Base discovery failures: split dense logs before buying more RPC

**Conclusion (updated November 4):** paid RPC is not justified. The formerly blocked historical cbBTC range now exports completely through the research relay: 20,873 unique logs in ten 1,000-block requests, with independently identical overlapping log sets. The human reported raising the relay response limit from 8 to 32 MiB and changing oversized-response cooldown handling. This verifies recovery of the diagnostic export, not current bot discovery completeness or live profit uplift. Broad 10k filters still require pagination because the observed total exceeds the upstream 20,000-result limit.

## Measurements (2026-11-03, research run e00f0030)

Sources: `scratch/research-e00f0030/all-markets.json`, `filter.json`,
`cbbtc-audit.json`, `cbbtc-paged-audit.json`, `cbbtc-recovery-audit.json`,
`cbbtc-dense-audit.json`; historical bot failures in
`scratch/review-2ceb4e18/runtime-summary.json` and attempts 38/39.
All chain queries used the relay research URL, never direct public endpoints.

At blocks **53458852–53468851**, using the paper bot's exact seven event topics
and market filter at Morpho `0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb`:

| Market prefix | 10,000 blocks | First 5,000 | Second 5,000 |
|---|---:|---:|---:|
| 09276541 (JitoSOL) | 94 logs | 47 | 47 |
| 7dc02ff6 (SOL) | 137 | 63 | 74 |
| e458a501 (cbZEC) | 84 | 30 | 54 |
| 9103c3b4 (cbBTC) | max-results error | 3,825 | upstream JSON parse failure |

The cbBTC 10k error is `-32602 query exceeds max results 20000`; its second
5k response reports `Unterminated string ... column 8388603 (char 8388602)`.
That is consistent with an **8 MiB truncation**, but the truncating component
is not established. Do not conclude the source returned only 3,825 events or
that raising a provider result cap alone fixes it.

Two 5k JitoSOL pages have exactly the same `(blockHash,transactionHash,logIndex)`
set as the full 10k query (94 unique logs). The first adaptive cbBTC export
split the size errors, then encountered `no provider available` / public HTTP
429 on the next child. It correctly failed with no output export. A subsequent
1k-page attempt retrieved nine sections (791, 758, 795, 708, 773, 780,
991, 980, 947 logs; total 7,523) before the last section
53467852–53468851 again hit the ~8 MiB parse boundary. Its split child, a
second full retry, and a subsequent 100-block-page attempt hit provider
unavailability. Complete recovery is not yet demonstrated. No failed export
file was published. Avoid more immediate retries while providers are unavailable.

Earlier paper failures: Aave 9 provider errors, Morpho 13 errors including
six repeated oversized-query failures at 17:31–17:56Z. Relay health at session
start: live 170418/1500000 CU, paper 109248/900000, research 14342/300000.
These counters rule out exhaustion of the displayed daily lane budgets at
that time; they do not rule out upstream rate limits or provider cooldowns.

## Free diagnostic improvement

`tools/relay-log-scan.py` exports through the research lane only, requires an
address and topics, defaults to 2k initial pages, splits explicit size errors
(including this observed upstream unterminated-string error), retries transient
availability failures twice with backoff **without splitting them**, and caps
requests (64 default; use 24 for small trials). Numeric start/end are inclusive.
It writes a separate completeness audit; a failed scan publishes no log export.
Output paths must be new. Test with:

`python3 scratch/research-e00f0030/test-log-scan.py`

Five offline tests cover exact split/page coverage, transient no-fanout retry,
request exhaustion and malformed/out-of-range rejection, and the observed
truncation error. This is research tooling, not a bot library. Earners implement
and measure any bot-specific fix within their own bot directory.

## Next measurement and decision

1. Let provider availability recover; try 1k pages over this same immutable
   historical range, max 24 requests. Preserve audit and compare overlapping
   log identities. If 1k still truncates, split further within the same cap.
2. Meta should inspect response-size handling and circuit-breaker/provider
   selection. A parse-size error should not unnecessarily disable unrelated
   small calls. No relay source outside the writable workspace was changed.
3. Earner should measure refresh completeness, highest fully processed block,
   age of candidate state, request count/CU, and errors before/after small
   incremental pages. Commit a cursor only after a complete range; preserve
   previous state on failure. Repeatedly rescanning 20k blocks every 5 min is
   avoidable. A healthy heartbeat is not proof of fresh discovery.
4. Only reconsider a paid endpoint if bounded incremental reads still fail
   during normal operation and otherwise safe executable opportunities are
   demonstrably missed. There is no measured capture/win-rate estimate today,
   so no recurring cost or human proposal is warranted.

Ledger context: `ledger top --chain base --days 7` at session start reports
Morpho actors d12810… 408 events, db61a2… 377, 4da50c… 297. These are event
counts, not profit or evidence of a latency advantage. This work repairs data
measurement; it does not establish an ability to beat those actors.


## Follow-up: complete recovery on 2026-11-04 (run 1df97b89)

Human decision `decisions/human/2026-11-04-inbox-replies.md` reports the response cap and cooldown fix. After that change, the exact previously failing immutable filter and interval were measured again through the research relay:

- Last 1,000 blocks 53467852–53468851: ten 100-block requests, **13,350 unique logs**, complete, no errors.
- Independent 1,000-block pages over 53466852–53468851: **14,297 logs**, two requests. The last-1k identities exactly match the 100-block-page export; the preceding 1k has 947 logs, matching the earlier audit.
- Full range 53458852–53468851: **20,873 unique logs**, ten 1,000-block requests, complete, zero errors, aggregate measured RPC time **3.551 seconds**. Each first-nine-page count exactly matches the prior November 3 audit: 791/758/795/708/773/780/991/980/947. Its last-2k and last-1k identity sets exactly match both independent exports.

Evidence: `scratch/research-1df97b89/cbbtc-{full,overlap,recovered}.json`, corresponding `*-audit.json`, and `cbbtc-comparison.json`. The broad 10k request was not repeated; the full count is already larger than its documented 20,000-result cap. This establishes complete recovery using bounded pages without a paid endpoint. No bot code was changed. Lead 8 can move from blocked_infra to measured for the diagnostic data-access question; earners still need their own complete-cursor and candidate-age measurements before claiming a bot improvement.
