---
type: method
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [any]
---
# Crash post-mortem: were there liquidations farm could take? (decision 2026-11-14-crash-postmortem-rival-contracts, part 1)

**Conclusion first:** after a market crash, measure from the ledger whether any liquidation was *counted* under race-rule-seconds and netted more than 1 USD after that block's gas. If none, write "急落時でも今の farm に取れる清算はなかった" and add no liquidation lead; if one or more, that source x chain becomes a lead and goes the normal way (fork proof, paper, review). First run: `infra/crash-2026-11-14.md` (deadline 2 days from 11-14, the ledger backfill is 7 days). Source: the decision file (Japanese; it wins if this page disagrees). Thresholds (72 h, 20 cases, 10 min, 1 USD, 3x) are the human's rough lines.

## 1-1. Scope (researcher)

- Window: the last 72 h; the 72 h before it as the comparison.
- Every liquidation source in the ledger, all nine chains (`ledger sources`).
- Per source x chain: count, repaid total, estimated gross (repaid x bonus), next to the previous 72 h.

## 1-2. Time to capture (earner)

Per source x chain up to 20 cases: the **10 largest gross and 10 with gross 1-50 USD** (slow captures, if any, are in the small band); all cases where fewer than 20. Per case:

- takeable time and block, captured time and block, difference in seconds (takeable = position health at the parent block, `methods/follow-slow-liquidators.md`)
- race-rule-seconds class: out / trial only / counted
- that tx's gas (gasUsed x that block's base fee + priority fee, USD; crash base fees, never normal-day numbers) and gross minus gas
- taker (EOA and executor; operator name from the census) and **taker type** (`methods/taker-types.md`)

Historical state reads use the research lane; watch the session's CU, largest sources first. A market that cannot be measured (oracle without events, ...) is written "not measurable" and skipped.

## 1-3. Left behind (earner)

Per source: positions that stayed liquidatable **10 minutes or more** without anyone taking them, or are still open. For each, find on the fork why (no exit for the collateral, too small for gas, permissioned liquidation, ...). If farm's executor takes one net-positive on the fork, it is a lead now.

## 1-4. Conclusion (researcher, on the wiki page)

- counted cases with net > 1 USD: count and total per source x chain
- which operators took them; whether the share taken slowly rose against the normal 72 h
- count of 1-3 leftovers, and whether any was taken on the fork
- share of gross taken by P+S+T vs B+O (`methods/taker-types.md`)

Meta forwards the result to `inbox/human/` in Japanese, title `crash-postmortem`.

## 1-5. Next time

When the ledger's liquidation count in some 24 h exceeds 3x the mean of the previous 7 days, the researcher starts the same post-mortem unprompted, on a new page `infra/crash-<date>.md`.

## Order of work (decision part 3)

1. earner: a waiting census A entry first (copy-other-bots item 5)
2. this post-mortem (2-day deadline, before the rest of the census timing)
3. rival-contract reading (`methods/executor-techniques.md`), top 5 first, one contract per session
4. the rest of the census
