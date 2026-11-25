# liquidator census: 18 days is enough (human, 2026-11-14)

- Treat the ledger history that exists (from 2026-10-26, about 18 days) as the census window. No backfill to 30 days.
- Write the actual window (first and last event date) next to every count and gross figure in infra/liquidator-census.md, and scale nothing up to 30 days.
- Chains without a liquidation source (bsc, polygon, avalanche, optimism, hyperevm) stay out of the census for now. If an operator found in step 1b is active there, name the protocol in the report; the researcher may add a source then.
