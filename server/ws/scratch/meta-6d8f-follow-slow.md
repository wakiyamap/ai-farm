---
type: method
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [aave_v3, morpho_blue, compound_v3]
---
# Follow slow liquidators (decision 2026-11-13-follow-slow-liquidators)

**Conclusion first:** stop picking a protocol and then asking whether we are fast enough. Instead list who earns liquidations (the census), measure how slowly each of them takes captures, and build only where slow takers win at least half of the gross. A market where fast takers win cannot be won by more measuring. Source: `decisions/human/2026-11-13-follow-slow-liquidators.md` (Japanese; it wins if this page disagrees). The thresholds below (3 s, 10 s, half, 300 USD) are the human's.

This census is the one exception to "liquidations are closed for new scouting" (`2026-11-08-beyond-liquidations.md`): a census-derived candidate (step 3) is a valid liquidation target. Census data lives in `infra/liquidator-census.md`; this page is the procedure.

## Step 1: census (researcher)

Over every liquidation source in the ledger on all 9 chains, last 30 days (`ledger top`, table `actor_daily`), one row per taker:

- addresses: the sending EOA(s) **and** the contract that executed the liquidation; several EOAs using one contract = one row
- count, total repaid USD, gross estimate (repaid x that market's liquidation bonus)
- split by chain / protocol / market
- build hints: flash loan or not, several liquidations batched in one tx or not, median priority fee paid

Put the top 30 by gross in `infra/liquidator-census.md`.

## Step 2: slowness per taker (earner)

For each of the top 30: take up to 10 of its captures and measure **seconds from becoming takeable to the capture** (the HF-ladder counting of the blocked_infra re-triage: `methods/blocked-infra-feed-retriage.md` step 2). Append per taker and per market: n measured, median s, minimum s, class.

- **fast**: median < 3 s (same block included)
- **slow**: median >= 10 s
- **middle**: in between
- market whose oracle emits no events (no takeable moment can be pinned): write `unmeasurable` and skip

Historical state reads use the research lane's Alchemy: watch the session's CU. Put `census taker <address>` at the start of the `attempts` target, one row per taker, and claim the taker (`claims/census-<first 8 hex>.json`). Find what is done with `kb query "SELECT id, target FROM attempts WHERE target LIKE 'census taker%' ORDER BY id DESC LIMIT 50"`.

## Step 3: pick targets (earner and researcher)

A chain x protocol x market is a candidate when all hold:

- slow takers took **at least half** of its 30-day gross
- that gross is **>= 300 USD**
- fast takers took it first only rarely, if ever

Per candidate, one KB lead (or extend the existing one) with: the slow takers' addresses, their median seconds, 30-day gross, the share fast takers took. Earners build bots from the top of the candidate list down; the usual rules (EV net of gas per occurrence, L, fork proof, feed rules) apply unchanged.

## Step 4: where else the slow takers earn (researcher)

For each slow taker: does the same address, or the same contract code, take liquidations or rewards on protocols or chains the ledger has no source for? Inside the 9 farm chains, add a ledger source; outside, report only the name and evidence (adding chains is the human's call). No paid services or keys.

## Running items (same decision, section 3)

- Lead 44 (Morpho Midnight, maturity time known in advance) continues; it is timed, not speed, so this decision does not touch it.
- Lead 17 (ethereum aave): windows exist (30-day recount: 4 captures, 54.66 USD); the poller (168 s revisit) was too slow. If step 2 finds this market's takers slow, rebuild it as a feed bot waiting on the Chainlink update.
- Leads 157 and 21 (base morpho): may be closed if the earner's measurement holds that the takeable part was a same-block race.
- Chain selection (both 11-13 chain decisions): done, no chain added; keep `infra/chain-selection.md` as is.

## Report

When steps 1-3 are complete, the researcher or meta writes a Japanese report to `inbox/human/` titled `liquidator-census` (table of steps 1-2 and the step 3 candidates). Interim results stay in the wiki; this can take several days.
