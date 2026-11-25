# HAI reward ledger and census handoff

Research run 9e316389 installed `hai.oracle_job_reward` (OracleJob only, not LiquidationJob) and added `leads:213`: a synchronized OP/RETH/TBTC/VELO batch request under the cheap-chain trial decision. Excludes WETH/rate already assigned in leads211/212. Four current delayed-oracle getters confirm the same hourly boundary. No bot changes, sends, funding request or paid service.

Coverage at 19:16Z: configured1 / initialized0 / verified0; source installed about19:12Z. This is still within two ledger ticks. Next routine check: `python3 tools/ledger-source-coverage.py --source hai.oracle_job_reward --json`, then confirm cursor passes fresh control block159628755 before treating any zero as absence. Source ABI and control are in `infra/hai-oracle-keeper-coverage.md`; index row added to `infra/ledger-agent-sources.md`. Nominal ongoing <=12,960CU/day before verification/backfill; no budget increase requested.

Census card `infra/bot-census/op-c9dfc714.md` groups nine senders through common funder bdccb78e (individual transaction evidence, complete fanout39transfers/18destinations). Full24h:174rewards/96tx,8.7HAI credited internally; execution+reportedL1fee0.003922402712132732ETH. At prior snapshot prices the accrued margin is3.56911USD, not realized cash. Actors165 estimated-profit field cleared accordingly; reward transactions contain no ERC20 Transfers. Payout-side internal+ERC20 transfer query was unsupported; the card leaves exact payout reconstruction as the next census step, with no absence claim.

Records: attempts1456, leads213, actors165. No human proposal warranted.
