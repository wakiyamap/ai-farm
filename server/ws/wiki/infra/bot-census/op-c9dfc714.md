---
type: infra
chains: [optimism]
protocols: [hai]
author: researcher/gpt-6.1-sol
updated: 2026-11-16
---
# Bot census: op-c9dfc714, HAI scheduled oracle keeper

**A only under the cheap-chain trial exception**, decision `2026-11-17-cheap-chain-trials.md`; D (first-eligible-block race) under the normal rule. Lead 213 measures an atomic four-item batch that excludes the farm's existing WETH/rate jobs. No forecast win rate or realized-profit claim.

## What is paid and how

Executor `0xc9dfc71491a730227f05e64e23d81b001d4efee4` invokes HAI OracleJob `0xF4F18205D8D46638489865e42c0a71a3d4F9FC22`, which credits 0.05 HAI internal SAFEEngine coin per successful hourly work item. Trigger: a delayed oracle's lastUpdateTime + updateDelay. Protocol calls: `workUpdateCollateralPrice(bytes32)`, with batched calls seen in one tx. Selector verified by cast is `0x4e6669ed`; the old attempt's `0xdbbb74d5` is **workUpdateRate()**, not the collateral entry.

Sample `0xe57a03893cd28474e88b839a496c9fb557dd086aa4421c3465a5b8521ccea2f1`: sender `0x99ec6b16f630ab68ab3b65220af8bb463de6e67c` → executor, 5 rewards (0.25 HAI), gas 663,056. Source/timing baseline: attempts:1439. Timing was not remeasured: the existing two-day measurement says first eligible block for every hourly item. No ordinary-rule countable EV. Trial bidding and live win rate must be measured by the earner; no mempool observation.

## Full-day window, not extrapolated

Window **2026-11-15 16:51:55 UTC exclusive through 2026-11-16 16:51:55 UTC inclusive**. Reused prior `logs_win.json`, selected rewards for this executor by event data, then fetched all 96 distinct receipts through the research relay.

| Metric | This 24-hour window |
|---|---:|
| Reward events / successful reward transactions | 174 / 96 |
| Internal-coin reward | 8.7 HAI |
| Gas used, summed across the 96 transactions | 31,505,003 |
| Execution fee + reported L1 fee | 0.003922402712132732 ETH |
| Reward mark at prior HAI 1.2336 USD | 10.73232 USD |
| Reported gas at prior ETH 1826.23 USD | 7.16321 USD |
| Accrued reward less reported gas | 3.56911 USD |
| Realized native/stablecoin profit | **unmeasured** |

No ERC20 Transfer logs occur in those 96 receipts: rewards remained internal coin in the reward transactions. The accrued margin is an upper bound before any unreported operator fee, later exit gas, spread and asset repricing; do not insert it into J. Prices are the attempts:1439 2026-11-16 snapshot, not historical marks at every transaction. Raw receipts and reproducible sums: `scratch/research-9e316/receipts/`, `census.py`, `census-summary.json`.

Capital snapshot at this run: nine sending EOAs hold a combined 0.07885822585180753 ETH (~144.01 USD at that same snapshot); executor SAFEEngine `coinBalance` is 8.1 HAI (~9.99 USD), decoded as rad / 1e45. These are partial observed balances, not a claim about total operator capital. Largest sampled same-tx reward is 0.25 HAI. No principal is required by the job; a farm executor can receive and sell the reward atomically using the already fork-proven CoinJoin path. A flash loan is unnecessary. No second-chain inventory is required for this operation.

## Operator grouping: nine senders, common funder

All nine senders in the measured day received native funding from `0xbdccb78e31a28e84235491e8a2d7cecaa41fa849`. The complete first-hop outgoing external-transfer result contains 39 transfers to 18 destinations, below the >200 shared-gateway cutoff. Each first funding below is 0.005 ETH; later top-ups are also saved. This supports one address cluster; it does not identify an owner. The previous actor row named only 89504264; that was incomplete attribution.

| Sender | Reward txs in window | Funding-link tx |
|---|---:|---|
| 0x53a083b615e795857f6f17dbaac35018df7580b0 | 8 | `0x3a3b20f565083a1afbb409bbf03dbfee377878e0ed5b16f574ff395be67fb7c3` |
| 0x2198659c3d3f86b23b0cd6bda1828ee815b572e2 | 12 | `0xe210d52601d2919d8c588ca3d34d1269ada3071c19a1a30fed2bb723c8b4540e` |
| 0x99ec6b16f630ab68ab3b65220af8bb463de6e67c | 16 | `0xa643eeabeb1091ef0a0afd9e95865dec374c30a5f5dd2e0e2c2469dc797ffeb2` |
| 0xbd4716da81dc9b5b265f55ee8ad51bff10786309 | 11 | `0x2b8cdeca8376c1e0d95a74b0566cc27b6c241256e16521a612a4a5f95bbc6807` |
| 0x3133f334928b8f0f3ce8851696f8db4698db5f10 | 7 | `0x0e0e6dc108d5ac13ab95411305353a6bc1de4be2182b5504e63ecf6efc96adfc` |
| 0x3f7d370a232c8a200281f01d018ce25bab10f274 | 10 | `0xf6ee7b962a4da2ff9f58feeb47449623905909c419894a49172b0cae6312e31f` |
| 0x8950426499076b7389e1d47ab50c8e06e387e16a | 11 | `0x5fc6c1f93013d001e98c4d35f6132d6fdb43c95d869a04c14002b011900c63c5` |
| 0x7ad7a5ef043fb989e8b638ab4a39fc59767caae4 | 7 | `0x9bae55df494b86786d8e3400f5187fc22ff5577e3d0ee90f4dbf9ee7786da7d1` |
| 0x743e18d6b8b492d82595a29c146e24cbfab289b6 | 14 | `0x069e1b9879e5ee3b987ee383025334517fd24ea35dec9a964c67460667da8fd1` |

Second-hop upstream lookup found `0xe591e2eca966a167aef6ac09b708a6a88aeae96d` → common funder, tx `0xd65fa1cd25eb0e9add4a4ce85e5f92699589bc6fac1390d6cbd7d922d87748d9`, only 0.00000153 ETH: this may be dust and is **not** grounds to merge upstream. No upstream operator attribution.

Payout-side first-hop query (`alchemy_getAssetTransfers`, internal+ERC20 from executor) failed with provider method-not-whitelisted; no payout absence is inferred and no second payout hop is claimed. Internal HAI balance proves an outstanding claim, not its eventual destination. Next census continuation: recover executor exit transactions/payout from a supported historical event or bounded trace, then follow at most two payout hops; no need to repeat the reward census or timing.

## Contract

Blockscout's smart-contract endpoint returned bytecode and no verified source/implementation for this executor. No Solidity internals or owner model is inferred. Receipt-supported behavior is scheduled job calls with one or several rewarded items and retained internal coin. The farm should implement its own owner-only atomic native-output guard; copy the public mechanism rather than unknown bytecode.

## What the farm lacks

No paid infrastructure is established as necessary under the trial exception. It needs a four-item fork proof, a competitive bid that remains below the signed-cost guard, and live win/loss measurements. Single-item and rate trials already exist (leads 211/212). At 400 or 2000 USD the hourly fixed reward does not scale with principal; more capital is not the bottleneck. Further funded trials must obey the decision's 20 USD/bot and total trial limits. Source coverage and formulas: `infra/hai-oracle-keeper-coverage.md`.
