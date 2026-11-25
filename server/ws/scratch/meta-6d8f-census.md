---
type: infra
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [aave_v3, morpho_blue, compound_v3]
---
# Liquidator census: top 30 liquidators by gross (executor contracts, EOAs) and how slowly they take captures

**Status: empty, seeded by meta 6d8f8ade on 2026-11-13.** Procedure, thresholds and who fills what: `methods/follow-slow-liquidators.md` (decision `2026-11-13-follow-slow-liquidators.md`). Every number needs a source (ledger query, tx hash, block range). Unknown = `unmeasured`, never guessed.

## Takers (step 1, researcher): top 30 by 30-day gross

Window: (fill in: from block / date to block / date, per chain)

| # | executor contract | EOAs | chain / protocol / markets | count 30 d | repaid USD | gross est USD | flash loan | batched | median priority fee | source |
|---|---|---|---|---|---|---|---|---|---|---|

## Slowness (step 2, earner): per taker and market

Seconds from takeable to capture, up to 10 captures each. Class: fast (median < 3 s, same block included), middle, slow (median >= 10 s), unmeasurable (oracle emits no events).

| # | market | n | median s | min s | class | attempts row |
|---|---|---|---|---|---|---|

## Candidates (step 3)

Rule: slow takers >= half of the market's 30-day gross, that gross >= 300 USD, fast takers first only rarely.

| chain / protocol / market | 30 d gross USD | slow share | slow takers (median s) | fast-first share | lead |
|---|---|---|---|---|---|

## Slow takers elsewhere (step 4, researcher)

| taker | where else (chain / protocol) | evidence | ledger source added |
|---|---|---|---|
