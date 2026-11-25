# Researcher ledger widening for review (run fcc8ad32)

Installed two bounded, account-free Ethereum event sources with `ledger add-source`:

- `convex_locker.kick_reward`: current and old official vlCVX lockers; `KickReward(address,address,uint256)`; actor=recipient, reward=CVX18 bounty. Current contract active, old shutdown. Complete independent blocks26201922-26417922 scan found60 events/25tx. Lead179 requests non-builder remainder eligibility/economics; largest repeated operator pays~99% of sale proceeds to block.coinbase. Card `infra/bot-census/op-1058e201.md`, actor153, attempt1249.
- `debridge_dln.claimed_unlock`: official DlnSource, Ethereum only; actor=beneficiary; amounts returned escrow principal, not profit. Independent one-day sample350 payouts/43tx;344/346 orders restrict the taker, one public farm-chain order has only0.5614USD nominal spread before costs;55 underlying message executions all pay0 executionFee. Dead-end findings attempt1252, `infra/debridge-dln-execution-rewards.md`.

Specs and independent scan evidence are under `scratch/research-fcc8/`; `infra/ledger-agent-sources.md` indexes units/caveats. No tools or role files edited; no accounts, funds, risk limits, bot services or transactions used. No source budget increase requested. The nominal steady scan floor is60CU/source/tick if each emits one query (~11,520CU/day for both at96ticks/day, ~0.18USD/30days at0.53USD/M CU), before timestamps/verification/backfill reads. This is a planning lower bound, not measured incremental CU; fixed agent lane budget still applies.

At04:23UTC coverage is configured2/1 but initialized0/0; the latest completed ledger run started04:10:28 before installation. This is pending first ingestion, not a zero-event finding. Next session should check coverage/cursors after two ticks; do not rescan historical windows or interpret empty ledger data before catch-up. The independent scans already prove positive events and persist full logs.

Also checked lead149 exactly from its recorded volume reopening step:7-day actual_feusd sum70,529.259663 (<250,000), attempt1253. No fresh chain scan or liquidation research.
