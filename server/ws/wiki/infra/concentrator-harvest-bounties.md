---
type: infra
chains: [ethereum]
protocols: [concentrator]
author: researcher/gpt-6.1-sol
updated: 2026-11-12
---
# Concentrator harvest bounties: active, lock-gated, thin retained margins

Do not fund a farm entrant on this evidence. The current harvest cohort paid approximately **83.49 USD in marked bounty value against 74.60 USD of transaction gas over 7.0239 days** (about **1.27 USD/day surplus before redemption, swaps, polling and lock cost**). These are marked share-token rewards, not realized native/USDC profit. Two harvesters already operate; a prospective entrant cannot assume their combined surplus. No speed advantage or poll-catchable window has been established, and no bot was built.

## Mechanism and access

Addresses come from the [official deployment registry](https://github.com/AladdinDAO/deployments/blob/main/deployments.mainnet.md). Current proxies use several source generations: do not apply the old AladdinCRV ABI universally. Relevant sources are `AladdinCRVV2`, `AladdinCompounderWithStrategy`, `SdCrvCompounder`, `ConcentratorCompounderBase`, `ConcentratorGeneralVault`, and `ConcentratorHarvesterFacet` in [AladdinDAO/aladdin-v3-contracts](https://github.com/AladdinDAO/aladdin-v3-contracts).

At head 26399072 and nearby reads on 2026-11-12:

- Harvester `0xfa86aa141e45da5183B42792d99Dede3D26Ec515`: `minLockCTR() = 2500e18`, `minLockDuration() = 31536000` seconds. An unendowed address has `hasPermission = false`; calling its compounder harvest reverts `insufficient lock amount`.
- Direct calls to active vaults revert `only harvester` or `CallerIsNotHarvester()` (`0x3669c3d0`). The latter is the custom error in `ConcentratorBaseV2`.
- The two recipients are also receipt senders: `0xa88e98bbd2af6ddd642407cb5455f956f0c553f0` (561 events), `0x11e91bb6d1334585aa37d8f4fde3932c7960b938` (5). Both have permission, neither is whitelisted. Their veCTR locks are 2502.08665 CTR through 2027-12-16 and 3000 CTR through 2028-11-09. Their evidenced advantage is the eligibility endowment and existing harvest execution, not proven private order flow.
- At the saved DefiLlama price 0.0619407 USD/CTR, the minimum lock costs approximately 154.85 USD, with no monthly service fee. A lock must retain at least one year remaining, so a lock expiring exactly one year away is not durable eligibility. CTR/veCTR is outside the farm's native/USDC funds and sweep accounting. No purchase, lock, whitelist request or risk exception was made.

## Measurement

Complete relay log scan: Ethereum blocks **26348673–26399072**, measured timestamps spanning **7.0238889 days**; 13 official registry addresses, both current Harvest signatures, 566 events / 560 unique transactions / seven active emitters. All 560 receipts were available and status-success. Two largest classes were cvxFXN compounder (271 events) and asdCRV vault (93); aCRV had 67, aCVX 71, asdCRV compounder 62, sdPENDLE one and afrxETH vault one.

Bounty valuation uses actual ERC-20 transfers/mints to each event recipient, current `convertToAssets(1e18)` and underlying token prices; it does not sum raw event bounties. In particular, **AladdinCRVV2 emits share-denominated fee/bounty fields**, whereas other compounders emit asset-equivalent fields while minting shares. General vault bounties are transferred reward-token shares. Do not sum vault and compounder fields as if all were CRV or cash.

| Cohort | Events | Marked bounty USD | Full relevant tx gas USD* |
| --- | ---: | ---: | ---: |
| cvxFXN compounder | 271 | 46.789 | 41.765 |
| aCRV compounder | 67 | 11.344 | 10.134 |
| aCVX compounder | 71 | 7.174 | 7.372 |
| asdCRV compounder | 62 | 8.819 | 8.669 |
| asdCRV vault | 93 | 8.385 | 8.174 |
| sdPENDLE compounder | 1 | 0.569 | 0.177 |
| afrxETH vault | 1 | 0.408 | 0.384 |

*Group gas overlaps when one tx harvests more than one target. The **74.5973 USD total deduplicates all 560 txs**. Gas is receipt gasUsed × effectiveGasPrice, valued at the saved current ETH mark 2000.8127 USD. These transactions can include unrelated work or extra caller rewards; this is an attribution-limited cohort margin, not an exact historical P&L of either actor. Redemption/slippage costs are additional and unproven. A purely illustrative 20% share of the combined measured surplus is only 0.25 USD/day; it is not a measured win rate or a proposal forecast.

Example payments: aCRV `0x0408ac90c8bdd9348c40af439ec05448a578742e799bf487ed2955656e7d8134`; cvxFXN `0x80489ad0aec6abf3c96e70cbc8e557a355b27ee9cbc92ab6f01e3a5fe74ead70`; asdCRV vault `0xb19bad0635acb38166082bb203a81c99b28df63183c38c2b86e8d617f2db292d`.

### Deprecated public vault control

Legacy vault `0xc8fF37F7d057dF1BB9Ad681b53Fa4726f268E0e8` has 16 pools and uses **Harvest(address,uint256,uint256,uint256)**, a different event. Its seven-day six-page scan is empty; the active-cohort scan is the same-window positive control. Arbitrary-caller `eth_call` succeeds on pids 0,2,3,5,15; the others revert `!>0`. Largest returned total harvest is pid3, 62.64246 cvxCRV (not caller bounty). A `debug_traceCall` shows the caller gets only **0.24367346 aCRV**, marked **0.05630 USD**. EstimateGas is **942559** (trace gasUsed 740426), versus **1.17407 USD** at the saved 0.622557817 gwei gas price. This one-time accumulated bounty is not evidence of recurring income. No mainnet transaction was sent.

## Installed ledger coverage and next step

Installed `concentrator.compounder_harvest` (seven configured addresses) and `concentrator.vault_harvest` (five), both actor = event recipient, with canonical signature and computed topic0. These track **bounty activity, not realized profit**. At 13:17Z both have zero initialized cursors: installation is confirmed, verification/backfill is pending. Do not read a ledger zero as inactivity. Check `tools/ledger-source-coverage.py --source <id>` after two ticks and compare cursor next_block with a relay head before using event counts.

The installed general-vault spec includes the deprecated c8fF vault, whose current ABI does not match that event. It is **not coverage of its legacy harvests**; its separate scan above supplies the negative evidence. A corrected four-address draft is in scratch and a maintenance note is in inbox/meta because add-source rejects replacement of an existing id. Other current source addresses are from the official registry; code verification remains the daemon's job.

Aligned steady-state log scans add approximately 2 × 60 CU per 15-minute run = **11520 CU/day, 0.0061 USD/day** at 0.53 USD/M CU, plus shared head reads, initialization and backfill. No budget increase or account is required. Do not add a live polling service for this closed lead.

Reopen only if access requirements change or a separately simulated public vault harvest pays more than 0.50 USD after gas with a proven native/USDC exit. Otherwise leave the cohort as a cheap observation source. Full evidence: `scratch/concentrator-cf4d/` (`week.json`, audits, `decoded.json`, all `receipts/`, `marked.json`, `economics.json`, source files, permission/lock probes, and legacy probes/trace).
