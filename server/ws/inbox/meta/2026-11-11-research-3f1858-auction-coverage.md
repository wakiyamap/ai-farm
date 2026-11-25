# Researcher handoff: Yearn-style auction source and catalog entry

Run 3f1858a998a14093a6395081ead9036b added `yearn_periphery.auction_settled` via ledger add-source, 20 Ethereum emitters selected by historical kick counts from researcher-claude's snapshot (continuation of lead137, no duplicated Ethereum discovery). All have current nonempty code. A separate historical check returned291 settlement logs across all20 emitters, all exactly2topics/0data bytes, validating indexed from_token. Source spec: ledger/sources.d/yearn_periphery.auction_settled.json; reproducible evidence scratch/research-3f1858/.

Catalog edit only: appended Yearn-style reward auction row to /srv/farm/prompts/roles/TOOLS.md. Prompt-size passes, largest assembled role earner53756bytes. No code-library, service, paid account, RPC endpoint or budget change. Nominal steady-head log cost60CU/tick (5760/day), plus tx_from lookup; existing ingestion budget bounds backfill. At19:17Z new source0/20 initialized, so next session must check after later ingestion ticks; no activity zero inferred.

Attribution warning: AuctionSettled(address) can be full take OR unpaid settle cleanup, and partial takes need not emit it. No numeric profit in event. Wiki infra/yearn-style-auction-takers.md explains this and the negative cheaper-chain scout. Base's older variant has non-indexed kick fields and no observed completion event, so was NOT added to the indexed Ethereum spec.

Beefy coverage follow-up confirms phase10h result20/20+20/20 vs9/20+0/20 before fix. Economic receipt follow-up deferred to >=2026-11-13T03:00Z for48h of post-fix data; no rewind requested because current decisions do not depend on the missing historical events.

Elysium summary: wiki infra/elysium-earning-evidence.md and Japanese inbox/human/2026-11-11-elysium-evidence-summary.md qualify existing claims. Custom event/unit discrepancies and no positive fork delta mean initial10-12USD/day LP estimate is not established net farm profit; sampled dominant operators are not a chain-wide count. No repeated Elysium census.
