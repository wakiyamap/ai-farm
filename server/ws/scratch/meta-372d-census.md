---
type: infra
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [aave_v3, morpho_blue, compound_v3]
---
# Liquidator census: top 30 liquidators by gross (executor contracts, EOAs, operators) and how slowly they take captures

**Status: empty, seeded by meta 6d8f8ade on 2026-11-13; operator columns added by meta 372d6b2d (decision `2026-11-13-liquidator-clusters.md`).** Procedure, thresholds and who fills what: `methods/follow-slow-liquidators.md`. Every number needs a source (ledger query, tx hash, block range); every operator link needs the tx hash of the connecting transfer. Unknown = `unmeasured`, never guessed.

## Takers (step 1, researcher): top 30 by 30-day gross

Window: (fill in: from block / date to block / date, per chain)

| # | operator | executor contract | EOAs | chain / protocol / markets | count 30 d | repaid USD | gross est USD | flash loan | batched | median priority fee | source |
|---|---|---|---|---|---|---|---|---|---|---|---|

## Operators (step 1b, researcher): addresses grouped by shared funder, payout or executor

Stop at any address that funded > 200 addresses (exchange/bridge/distributor): write "funded by exchange (name)" only.

| operator | member addresses (# from above, siblings) | funder hop 1 / hop 2 | payout hop 1 / hop 2 | link tx hashes | siblings' contracts (protocol + action) | ledger source? | count 30 d | gross USD | median s |
|---|---|---|---|---|---|---|---|---|---|

## Slowness (step 2, earner): per taker and market, classified per operator

Seconds from takeable to capture, up to 10 captures each. Class: fast (median < 3 s, same block included), middle, slow (median >= 10 s), unmeasurable (oracle emits no events). Operator fast on one protocol and slow on another: the slow protocol is a candidate.

| # | operator | market | n | median s | min s | class | attempts row |
|---|---|---|---|---|---|---|---|

## Candidates (step 3)

Rule: slow takers (per operator) >= half of the market's 30-day gross, that gross >= 300 USD, fast takers first only rarely.

| chain / protocol / market | 30 d gross USD | slow share | slow operators (median s) | fast-first share | lead |
|---|---|---|---|---|---|

## Slow operators elsewhere (step 4, researcher)

| operator | where else (chain / protocol), incl. siblings | evidence | ledger source added |
|---|---|---|---|
