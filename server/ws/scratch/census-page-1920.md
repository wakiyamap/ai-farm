---
type: infra
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [aave_v3, morpho_blue, compound_v3, moonwell, compound_v2, exactly, llamalend, sparklend, revert_lend]
author: earner/qwen3.8-flash-next
updated: 2026-11-14
---
# Liquidator census: provisional ranking and operator traces through rank10

**Conclusion: the coverage-limited ranking and operator traces through ranks6–10 are recorded, and the step-2 slowness measurement now covers ranks1–15 and 17–20: the four Base Morpho labels were withdrawn after the historical accrued-HF correction (all four sampled takers fast in sample), the four ethereum ranks 2/3/6/7 were measured 2026-11-14 fast in sample on their sampled aave_v3/morpho_blue captures, ranks11–14 were measured 2026-11-14 (run 171d32b6): ranks11/13/14 fast in sample, rank12 intermediate (median 0.5 blocks / 6 s — its whale gross sits in same-block captures; its single ≥2-block window event is a 11.89 USD-debt capture, cents at farm scale), and ranks15/17/18 were measured 2026-11-14 (run 329ef7a8): all three fast in sample (rank15 median 0 blocks with two 1-block small-debt exceptions; ranks17/18 all healthy at C−1), and ranks19/20 were measured 2026-11-14 (run d268c806): rank19 fast in sample on its 12 aave_v3 events (one 1-block/12 s parent-eligible exception — the L-block trial band of decision 2026-11-14-race-rule-seconds, not counted in EV; its 6 compound_v3 absorbs carry the protocol-level 0-block classification of attempts 1055/1069, the new C-1 price probe reverted on all function-shape controls), rank20 fast in sample (all 12 events cross inside the capture block; four 1-block = 0.2 s parent-eligible exceptions at one batch). No slow-market candidate (median ≥10 s) is established by this sample.** The earlier four Base Morpho "slow" labels were oracle-age measurements, not eligibility windows. Historical accrued HF checks now find466/469 sampled events healthy at the parent; all four representative taker medians are0s. Rank8 joins ed989 through private funding links. No new slow-market lead or infrastructure purchase is justified by this sample. Never merge solvers through Atlas, relayers, builders, or >200-recipient funding gateways. Procedure: `methods/follow-slow-liquidators.md`. Correction and batch6–10 evidence: `infra/liquidator-census-evidence-2026-11-13-batch6-10.md`.

## Coverage and valuation

Run `4170e414a73c436385e8cb192708bc6f`, snapshot cutoff 2026-11-13 13:10:06 UTC. Requested interval: 2026-10-14 13:10:06 through cutoff (`1791983406 <= ts <= 1794575406`). Export: `scratch/census-4170/events.json`, 11,638 events, 20 nonempty source/chain combinations; all configured liquidation sources were queried, including zero-event sources. Earliest recorded liquidation is 2026-10-26; the ledger does not prove a complete 30-day backfill. Cursor-at-head is not proof of historical completeness.

11,551 candidate earning events remain after separating 84 unpaid Compound absorbs and 3 explicit LlamaLend self-liquidations. Of these 11,541 have a nominal valuation; 10 remain unpriced. They form 553 chain/address rows, not 553 independent operators. Priced repayment totals $149,203,814.65; nominal incentive estimate $7,614,830.80. These are **coverage-limited incentive proxies, not realized profit, achievable farm revenue, or a complete 30-day total**.

Prices: DefiLlama historical daily noon observations (confidence >=0.8, requested search width 12h), raw responses `prices-*.json`; token decimals checked on-chain for the 224 market keys. Incentives use current contract parameters, not historical per-event/eMode configurations. Aave eMode overrides, protocol seize/bonus fees, swaps, auction bids, gas and monitoring are not subtracted. Morpho uses its LLTV incentive; Compound buyCollateral uses `1/(1-storeFrontPriceFactor*(1-liquidationFactor))-1`, not daily collateral-price differences. Revert uses fullValue-cost and Exactly the liquidator incentive. Thus this is a prioritization index; finalize historical/effective bonuses before step-3 thresholds. Metadata error: one deprecated cUSDT market could not read the current incentive.

| chain | recorded liquidation-related events | recorded block span | oldest → newest event UTC |
|---|---|---:|---|
| base | 10429 | 53147160–56903958 | 10-27 06:47 → 11-13 11:59 |
| arbitrum | 282 | 518442186–523779862 | 10-26 12:42 → 11-13 05:56 |
| ethereum | 886 | 26284068–26405342 | 10-27 12:32 → 11-13 10:07 |
| hyperevm | 41 | 50393819–51121525 | 11-04 20:34 → 11-13 03:26 |
| bsc | 0 recorded | no recorded liquidation rows | not a chain-wide zero claim |
| polygon | 0 recorded | no recorded liquidation rows | not a chain-wide zero claim |
| avalanche | 0 recorded | no recorded liquidation rows | not a chain-wide zero claim |
| optimism | 0 recorded | no recorded liquidation rows | not a chain-wide zero claim |
| elysium | 0 recorded | no recorded liquidation rows | not a chain-wide zero claim |

## Takers: top 30 by nominal gross in the available window

EOAs, full protocol/market splits, sampled tx hashes and funding links are in `infra/liquidator-census-evidence-2026-11-13.md`. Priority fees are medians of up to 10 evenly spaced **transactions**, not all events. `flash ?` means not established; one positive receipt event suffices for yes. Batch size counts only indexed earning events in one tx. HyperEVM rows identify the event receiver; the executing caller still needs verification.

| # | operator | executor / event taker | chain; protocols | events / txs | repaid USD | nominal gross USD | flash | batch max | median tip gwei (n) |
|---|---|---|---|---:|---:|---:|---|---:|---|
| 1 | payout51c* | `0x9cbb82b990ed997d440db1119d07519777c00005` | base; morpho_blue | 1161 / 88 | 33,412,582.50 | 1,669,085.64 | yes sampled | 30 | 15 (10) |
| 2 | payout51c* | `0xeef1b06e23a39f05b6b34ff1052d7a6ca3a00005` | ethereum; aave_v3,compound_v3,morpho_blue | 9 / 8 | 24,396,951.08 | 1,105,312.85 | yes sampled | 2 | 0 (8) |
| 3 | bc034 | `0xbc034f2327b1d2fc51fe9e197dbc35c17f592672` | ethereum; aave_v3,compound_v2,compound_v3,morpho_blue | 33 / 14 | 15,496,294.95 | 771,209.09 | yes sampled | 7 | 0 (10) |
| 4 | d128 | `0xd12810b19b596347a3afac206d3ca65d08594b3f` | base; aave_v3,compound_v3,morpho_blue | 724 / 90 | 9,814,185.18 | 543,589.63 | yes sampled | 38 | 7.64414 (10) |
| 5 | ed989 | `0xed989ee258ecc93769a8478c9973667b17462dfe` | base; morpho_blue | 452 / 40 | 7,472,331.38 | 358,195.80 | yes sampled | 30 | 15 (10) |
| 6 | exec2945 | `0x29452e8332912533130fb708984722d92184284f` | ethereum; aave_v3 | 70 / 23 | 6,306,663.65 | 327,838.42 | yes sampled | 19 | 0 (10) |
| 7 | exece14c | `0xe14c836bd3b0be1d4b52ac4d4f00c163926ff069` | ethereum; aave_v3,morpho_blue | 9 / 9 | 7,400,848.19 | 324,957.13 | yes sampled | 1 | 0 (9) |
| 8 | ed989 | `0x91d682699cf4dbfb8a5ea4e860bf29f76ede99cd` | base; morpho_blue | 567 / 88 | 3,270,406.44 | 296,852.77 | yes sampled | 36 | 0.0961339 (10) |
| 9 | ed989 | `0xdb61a25516b4480df393d7bfe2d8e33fdaaf079a` | base; morpho_blue | 377 / 68 | 2,948,360.00 | 197,844.58 | yes sampled | 15 | 0.0415829 (10) |
| 10 | exec5ab7 | `0x5ab72cb36cdc5a17b637b55dbbf41f2f349b3fea` | base; morpho_blue | 225 / 23 | 2,890,789.43 | 142,820.49 | ? | 35 | 15 (10) |
| 11 | unclustered | `0xf000042d2b48921c234f15d167e7874f594f303e` | ethereum; morpho_blue | 3 / 3 | 3,209,444.40 | 140,706.33 | yes sampled | 1 | 0 (3) |
| 12 | unclustered | `0x789e3f3cad898948759402b347d1d1e007f93f79` | ethereum; aave_v3 | 4 / 4 | 2,722,737.13 | 136,136.86 | ? | 1 | 0 (4) |
| 13 | unclustered | `0x6109bc698ffd20de8114ec4c9291052a6ceff9f7` | base; morpho_blue | 92 / 4 | 2,385,836.06 | 108,638.79 | ? | 26 | 0.205103 (4) |
| 14 | unclustered | `0xe4d797c8a24d531c8ee3e21d6cfa9605eae54e4b` | base; morpho_blue | 14 / 1 | 2,425,645.69 | 106,343.55 | yes sampled | 14 | 15 (1) |
| 15 | unclustered | `0xf28307728ad7b7449e9b020a5c24292ce5f871ca` | ethereum; aave_v3 | 61 / 12 | 2,110,494.35 | 104,349.33 | yes sampled | 11 | 0 (10) |
| 16 | unclustered | receiver `0x9466140c8781e253fe426c87ac17ccba500140ff` | hyperevm; morpho_blue | 2 / 2 | 552,287.10 | 70,008.22 | yes sampled | 1 | 6 (2) |
| 17 | unclustered | `0x7372825fd055d2ed613283419af846a53cdcbfb6` | base; morpho_blue | 25 / 25 | 1,532,957.00 | 69,914.63 | ? | 1 | 105.955 (10) |
| 18 | unclustered | `0xbd0dd817c608e552d5f1ae701ab6c4da4fb00005` | base; morpho_blue | 52 / 10 | 540,882.49 | 61,047.26 | yes sampled | 10 | 15 (10) |
| 19 | unclustered | `0xbde3e91f09a9489f1b53eaa21eb32c89b2fd5c64` | ethereum; aave_v3,compound_v3 | 17 / 8 | 995,859.69 | 52,486.40 | yes sampled | 7 | 0.01 (8) |
| 20 | unclustered | `0x3e9a355fa4305370cc64c14a8f03cb27a11c3c86` | base; morpho_blue | 12 / 12 | 1,117,903.54 | 49,010.38 | ? | 1 | 56.0597 (10) |
| 21 | unclustered | `0x557d0f989621387892342c390bec9cc7c74d5d89` | ethereum; aave_v3 | 4 / 4 | 648,124.17 | 48,540.01 | yes sampled | 1 | 0 (4) |
| 22 | unclustered | `0xd8413bf7e7782b536abdeebbcb9e7c4fc481e2e7` | base; aave_v3,morpho_blue | 255 / 48 | 807,770.89 | 42,820.10 | ? | 44 | 0.314025 (10) |
| 23 | unclustered | `0x2ea89fc4b65ed6fa0494b6c9b15403bf1137907f` | base; morpho_blue | 23 / 3 | 920,773.73 | 41,185.15 | ? | 20 | 0.161971 (3) |
| 24 | unclustered | receiver `0x281354062fa932086890a6bbf7dff7d0a67d220f` | hyperevm; morpho_blue | 1 / 1 | 433,244.99 | 32,109.46 | ? | 1 | 250 (1) |
| 25 | unclustered | `0x65f14ba7984512c9aa552f133c248075b488b9ee` | base; compound_v3 | 1 / 1 | 1,019,021.64 | 31,516.13 | ? | 1 | 15 (1) |
| 26 | unclustered | `0x83557c6d286553ad103bb08f0c04ec25724c0e06` | base; morpho_blue | 34 / 34 | 415,818.08 | 30,817.88 | ? | 1 | 110.045 (10) |
| 27 | unclustered | `0xecd48b7dc7862f5d529121f6e5d6ed4b0774f2ca` | base; morpho_blue | 18 / 16 | 674,056.49 | 30,537.74 | ? | 2 | 123.564 (10) |
| 28 | unclustered | `0x9d5b90baf46e622b348e49b9e2ac872c5bbf5f7d` | ethereum; aave_v3,morpho_blue | 14 / 2 | 557,271.02 | 30,349.07 | yes sampled | 13 | 0 (2) |
| 29 | unclustered | `0x0268e896b6b1b06f58b4828551e895856914f828` | base; morpho_blue | 151 / 14 | 544,375.88 | 28,664.87 | yes sampled | 40 | 7.35295 (10) |
| 30 | d128 | `0xd12810b19b596347a3afac206d3ca65d08594b3f` | arbitrum; aave_v3,compound_v3 | 109 / 51 | 480,954.36 | 28,554.56 | yes sampled | 7 | 0.0187747 (10) |

## Operators: first ten takers, plus evidenced siblings

Funding/payout graph is limited to two hops; links beyond a >200-recipient distributor are excluded. No owner identities are inferred. `payout51c*` is a **provisional cross-chain shared-payout grouping**, not an ownership assertion: the address has different runtime code on Base and Ethereum. Both payment links are verified; finish its internal-recipient gateway check before treating that aggregation as step-3 evidence. Native external outgoing transfers from that contract are zero on both chains; first 1,000 native/internal transfers have 2 and 11 recipients respectively, but pagination remains.

| operator | member takers / siblings | funding and payout evidence | events | repaid USD | nominal gross USD | median seconds |
|---|---|---|---:|---:|---:|---|
| payout51c* | #1, #2 | #1 Base + #2 Ethereum; same payout address `0x51c72848c68a965f66fa7a88855f9f7784502a7f`. #1 signer funder `714d7557…` ← `2466a853…`; #2 sampled senders funded by `5d476039…`, whose own funder `f7858da8…` is a >200-recipient boundary. Payouts: traces `0xe7d413cf4916b5015d724aa57fdfc33506bd055f3479fb0e9c65ba5c85d1d7c7` and `0xf5ff0c7106886a61fddb7a03ab7da7b3ae50cd4ba62e1f418b7a07f98434a3eb`. | 1170 | 57,809,533.58 | 2,774,398.49 | Ethereum rank2 measured fast in sample 2026-11-14 (see Slowness below) |
| bc034 | #3, #124 | #3 + sibling #124 `0x74edc79fea13bdf1f7841570227127cec493bdd9`, funded by `d694da17…` (11 native recipients). Sibling funding tx `0x6cac565d8e3b641a001cedd8d57ef724da6ed77c9d4d89b7d74f520f2dbbfdcf`; #3 EOA funding tx `0x381d56ed4eaa0660eda7e4a38708c5ecc9faadc8d90bf7c93d129ef0d63e2fe3`. The sampled `dadb0d80…` transfer is to that block’s coinbase, not an operator payout; it also has350 native recipients. Stop and never merge through builder payments. | 48 | 15,536,894.41 | 772,223.41 | Ethereum measured fast in sample 2026-11-14 |
| d128 | #4, #30 | #4 Base + #30 Arbitrum: identical 170-byte executor runtime at the same address (SHA256 of hex runtime `8ff0c472b3f40103…`, artifact `sibling-probes.json`), and sampled txs execute that contract on both chains. Private Base funding path signer ← `5dc11035…` ← `23d7424e…`; other signer funder `d971c15f…` has 488 native recipients, stop. Observed payout path D128 → `23d7424e…` (tx `0x408e232d5371505ef81092407e888c6e8c7f8eb5529a934ba2c43a4379709314`) → `5dc11035…` (tx `0xde9fc73dd4c004944d62b9cafe684d83b163c9397c8c1f2cc377dc9b56d4e6d4`). The Atlas execution environment is not a payout wallet. | 833 | 10,295,139.54 | 572,144.19 | unmeasured |
| ed989 | #5, #8, #9, #43, #387 | #5 + #9 `db61a255…`, #43 `b8a26b3c…`, #387 `db590332…`. #5 and #43 share funder `4862a125…` (22 native recipients), #5 signer and #9/#387 share `697c6cd9…` (38). #9 link `0x94d8d3e34940c866160b87780df9a11346594b0cbf24c0d6bac72f2098ccacdb`; #43 link `0x96deba5ddea21831c44e54895171b77d0e36a617cc7d3db3469116aa998af6b7`. Both funder reach `befa750e…` (715 native recipients): stop. #5 payout is `9af4392e…`, which pays `697c6cd9…` (tx `0xf1d2e8522d56af3bcc994e4db567a1c328fc183d9a50baaee4315d0bfcc76e07`) and `4862a125…` (tx `0xe378035aeb38c2b1eecc18c355360e0403b518302fadabc3dc68d318beae5916`). Its `39b1bc83…` funding edge is incoming, not payout. | 1504 | 13,836,461.16 | 867,676.07 | Base sampled ranks5+8 median0s; rank9 measured fast in sample 2026-11-13 |

The sibling contracts with existing ledger activity use Morpho, Compound v2/v3 and LlamaLend, all already indexed. No missing-source protocol has been established. The funding-edge candidate inventory has 410 distinct recipients; these are **not** 410 proved sibling bots. Gateway-adjacent or unclassified recipients remain candidates only. The first five graph pass still has bounded pagination and payout-hop work; finish those recorded gaps before calling step 1b complete. Ranks6–10 were continued below; next new funding batch is11–15. Preserve existing shared-operator links and the recorded pagination gaps.

## Ranks6–10 continuation (run a33d4ea2, 2026-11-13)

Rank8's six sampled execution wallets receive direct native funding from existing ed989 funder `697c6cd9…` (38 recipients); two also from `4862a125…` (22). Example rank8 solver `55264f50…` funding tx `0xf4235d31e815415f74f6e3662a473a65fa7ea80cbb8f6496e04a857c88beabc5`; rank8 direct sender `fe5d0060…` funding tx `0x3f55ebbce74a499c94d358796713133eacb24e6bfd56ad304482f37837bc2832`. These private links add rank8 to ed989; the 451-recipient multisender `49cb8c4c…` is excluded. Full addresses/links: `infra/liquidator-census-evidence-2026-11-13-batch6-10.md`.

| operator | member rank | events | repaid USD | nominal gross USD | median seconds |
|---|---|---:|---:|---:|---|
| exec2945 |6; seven sampled direct senders share executor|70|6,306,663.65|327,838.42|measured fast in sample 2026-11-14 (ethereum aave, see Slowness below)|
| exece14c |7; one sampled direct sender|9|7,400,848.19|324,957.13|measured fast in sample 2026-11-14|
| exec5ab7 |10; three sampled Atlas solver signers|225|2,890,789.43|142,820.49|0, representative Base Morpho sample|

Rank6 first gas funding reaches `d152f549…` (>=980 recipients); rank7 reaches `c618990a…` (>=890); rank10 reaches `3ad7bca0…` (>=308 after8 pages). Stop at all three. Rank6 pays surplus to execution senders; rank7 has verified WETH withdrawals to its sender. Rank8/rank10's shared native destination `1c6ec845…` is an Atlas execution environment and cannot link operators. Rank10's actual earnings payout remains unresolved. Privately funded sibling contracts have Morpho repayments and/or ed989 payout transfers; no missing-source earning protocol has been proved. Next new funding batch11–15, while recorded payout and first-five pagination gaps remain open.

## Why nominal gross is not profit

Sample #1 tx `0xe7d413cf4916b5015d724aa57fdfc33506bd055f3479fb0e9c65ba5c85d1d7c7`: executor sends 0.9239619762 ETH to the Atlas execution environment, while 0.0226925363 WETH goes to the shared payout contract. Sample #2 `0xf5ff0c7106886a61fddb7a03ab7da7b3ae50cd4ba62e1f418b7a07f98434a3eb`: 236.1712278278 ETH goes to `0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97`, 41.6782048031 WETH to the payout contract. These are observed transfers, not whole-transaction net profit. Samples can batch many liquidations; do not compare a single event incentive to the entire tx payout.

## Slowness (step 2): corrected historical HF checks

The earlier claims in attempts1121/1122/1137/1138 are superseded for the sampled Base Morpho captures. Their script measured the last wrapper-price change **before C−1**, without checking C−1 borrower HF or the oracle change inside C. No-change caps are not eligibility lower bounds.

Run a33d4ea2 reused those exact40 transaction selections. Each accrued historical eth_call reads real marketParams, `accrueInterest`, market totals, wrapper price and borrower position. Every indexed liquidation for that executor in each sampled tx was checked, not only the largest event. `scratch/census-a33d/hf-parent.json`, `all-sampled-events-hf.json`, `hf-validation.json`, `hf-windows.json`; full formula, direct-call controls and hashes in `infra/liquidator-census-evidence-2026-11-13-batch6-10.md`.

| rank / operator | chain / protocol | sampled txs | indexed events | healthy at C−1 | representative median s | class |
|---|---|---:|---:|---:|---:|---|
|1 / payout51c|base / morpho_blue|10|171|171|0|fast in sample|
|5 / ed989|base / morpho_blue|10|148|148|0|fast in sample|
|8 / ed989|base / morpho_blue|10|72|69|0|fast in sample|
|10 / exec5ab7|base / morpho_blue|10|78|78|0|fast in sample|

Combined sampled Base ed989 representative median:0s (20 txs from ranks5+8). Ethereum members were measured 2026-11-14 (run de3e913b, below); rank9 and rank4 were measured 2026-11-13 (attempts1152/1153: fast in sample). Of $415,029.16 sampled nominal gross, only $0.562117 is parent-eligible (three rank8 dust events, $4.554120 repaid). The largest SOL dust event crosses at C−1 (1 block/1s; never counted EV); the cbBTC dust crosses at C−7 (7 blocks/1s; $0.008019 nominal gross). The second SOL dust crossing is unmeasured ($0.019171 gross). Five direct liquidation prechecks independently return `position is healthy`; the eligible SOL control instead reaches `transferFrom reverted`. No new farm revenue is claimed.

Begin with actual eligibility before any backwards ladder. The old oracle-age medians152/76.5/46.5/151.5s cannot support step3. Continue other ranked takers with HF checks; do not rebuild these four sample sets from scratch.

## Slowness (step 2): ethereum ranks 2/3/6/7 (run de3e913b, 2026-11-14)

Measured with the same eligibility machinery (historical state eth_calls, research lane, ~380 reads): aave_v3 via the mainnet Pool `0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2` `getUserAccountData` ladder at C−1..C−64, and morpho_blue via the a33d accrued `accrueInterest`→market totals→oracle `price()`→`position` state at C−1. **The ethereum mainnet new-core Pool puts the 1e18-scale health factor in the 6th return word, not the 5th (see `pitfalls/aave-new-core-useraccountdata-words.md`); reading the 5th word misclassifies every capture as underwater.** Outputs: `scratch/census-eth/out.json` (aave ladder) and `scratch/census-eth/morpho-parent.json` (morpho C−1 states).

| rank / operator | chain / protocol | sampled txs | indexed events | healthy at C−1 | window finding | class |
|---|---|---:|---:|---:|---:|---|
|2 / payout51c|ethereum / aave_v3|4|4|4|all cross inside the capture block|fast in sample|
|2 / payout51c|ethereum / morpho_blue|2|2|2|hf 1.004464 / 1.007477 at C−1|fast in sample|
|3 / bc034|ethereum / aave_v3|5|18|14|four cascade rows crossed at C−2/C−3 (1–2 blocks ≈ 12–24 s, the aave-pricefeed-ethereum cascade blocks 26372985–88)|fast in sample (median 0 blocks)|
|3 / bc034|ethereum / morpho_blue|7|11|10|one eligible at C−1 (26372987 borrower 0xb8f089c8, hf 0.996364, window ≥1 block)|fast in sample (median 0 blocks)|
|6 / exec2945|ethereum / aave_v3|10|15|15|all cross inside the capture block|fast in sample|
|7 / exece14c|ethereum / aave_v3|4|4|4|all cross inside the capture block|fast in sample|
|7 / exece14c|ethereum / morpho_blue|5|5|4|one eligible at C−1 (26338330 borrower 0x42ac60ae, hf 0.999815, window ≥1 block)|fast in sample (median 0 blocks)|

compound_v3 events of ranks2/3 (3 each) were not measured (few events; left to the next batch). The parent-eligible exceptions (bc034 26372987, exece14c 26338330) are the ethereum minority-crossing shape the aave-pricefeed-ethereum bot counts as 1–2 block windows — they exist but are rare, not the median. **All four ethereum ranks classify fast in sample on their sampled protocols; with ranks1/4/5/8/9/10 measured fast, no slow taker exists among census ranks1–10, so step3 (candidates from slow takers) stays zero for now.** Next census batches: ranks11–15 funding links (step 1b) and their step-2 slowness (the step-2 half of ranks11–14 measured below).

## Slowness (step 2): ranks 11–14 (run 171d32b6, 2026-11-14)

Measured with the same eligibility machinery (historical state eth_calls, research lane, ~130 cached reads; script `scratch/census-r114/run.py`, outputs `scratch/census-r114/windows.json`): morpho_blue via the a33d accrued `accrueInterest`→market totals→oracle `price()`→`position` state at C−1 (backwards ladder C−2..C−64 only for the C−1-eligible), aave_v3 via `getUserAccountData` word6 HF at the ethereum Pool `0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2` and the Base Pool `0xa238dd80c259a72e81d7e4664a9801593f98d1c5`, ladder C−1..C−4. Multicall3 batches go through `0xca11bde05977b3631167028862be2a173976ca11` (bytecode non-empty control at both chains).

| rank / operator | chain / protocol | sampled txs | indexed events | healthy at C−1 | window finding | class |
|---|---|---:|---:|---:|---:|---|
|11 / 0xf000042d|ethereum / morpho_blue|3|3|3|hf 1.0011–1.0012 at C−1; all cross inside the capture block (blocks 26372986–26372988 = the lead 14 pinned-market price-drop run)|fast in sample|
|11 / 0xf000042d|base / aave_v3|2|2|2|hf ≥1 at C−1 (captures 56748477, 56795151, after the Base 0.2 s block speedup)|fast in sample|
|12 / 0x789e3f3c|ethereum / aave_v3|4|4|2|windows [≥2, 0, 1, 0] blocks = [24, 0, 12, 0] s; median 0.5 blocks / 6 s, min 0 s; the sole ≥2-block event (block 26300864, tx `0x01cba12fc78efe18caa0f4d2496d62d330141b8fda433b4cff31a168063a2b47`) is an 11.89 USD-debt capture, gross ≈1.2 USD|intermediate (median in the 3–10 s band)|
|13 / 0x6109bc69|base / morpho_blue|4|92|92|hf 1.00003–1.0033 at C−1; batch captures 14–26 events per tx, all cross inside the capture block|fast in sample|
|14 / 0xe4d797c8|base / morpho_blue|1|14|14|hf 1.000007–1.001194 at C−1, windows 0 (tx `0xa3a853d9a0755b051d00a01b0be9e814f3080a1a1ce9434a7493f6fbfa1a4891`)|fast in sample|

rank11's compound_v3 events (1 arbitrum + 1 base) were not measured (single events). The census rank11 row is snapshot-limited to its ethereum morpho captures; its base aave captures postdate the 11-13 13:10Z cutoff. Rank12's whale gross (136,136 USD nominal) sits in the same-block captures — its 26372984 event carries a 2,724,061.94 USD debtToCover and crossed inside the capture block — while its parent-eligible exceptions are small-debt captures (11.89 and 33.06 USD debtToCover), the same minority-crossing shape the closed lead 17 band counts as 1–2 block windows with cents of farm-scale gross. **No ranks11–14 taker classifies slow (median ≥10 s); step3 candidates stay zero.** Next: ranks15+ step-2 slowness and the ranks11–15 funding batch (step 1b).

## Slowness (step 2): ranks 15/17/18 (run 329ef7a8, 2026-11-14)

Measured with the same eligibility machinery (historical state eth_calls, research lane, ~140 cached reads; script `scratch/census-r1518/run.py`, outputs `scratch/census-r1518/windows.json`): morpho_blue via the a33d accrued `accrueInterest`→market totals→oracle `price()`→`position` state at C−1 (backwards ladder C−2..C−64 only for the C−1-eligible), aave_v3 via `getUserAccountData` HF at the ethereum Pool `0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2` (6-word return, HF in word 6; a 386-char return probe precedes the ladder), ladder C−1..C−64. Multicall3 `0xca11bde05977b3631167028862be2a173976ca11` on base.

| rank / operator | chain / protocol | sampled txs | indexed events | healthy at C−1 | window finding | class |
|---|---|---:|---:|---:|---:|---|
|15 / 0xf2830772|ethereum / aave_v3|11|56|54|two parent-eligible 1-block windows (12 s): block 26399072 tx `0x77893ad89da1ed2a0f594057dd4629cad3ea8f7d2dd7e1818015c4ed90c86b74` debtToCover 152.18 USD and 26403972 tx `0xdd23a2490ab4737104ece8e7008bdc3918c8dd72a05018d4b3b4044661c14cd9` 19.77 USD — both in the cascade run the closed lead 17 band counts as 1-block (not countable EV); the 26399072 capture is in the same cascade as the lead 17 capture 26399074|fast in sample (median 0 blocks)|
|17 / 0x7372825f|base / morpho_blue|10|10|10|hf 1.00025–1.005291 at C−1; all cross inside the capture block (blocks 53485941–55160612, mostly after the Base 0.2 s block speedup)|fast in sample|
|18 / 0xbd0dd817|base / morpho_blue|10|52|52|hf 1.000143–1.009432 at C−1; all cross inside the capture block|fast in sample|

Rank15's whale gross (104,349 USD nominal) sits entirely in same-block captures; its parent-eligible exceptions are 1-block small-debt captures — cents of farm-scale gross and not countable EV per decisions/human/2026-11-13-next-block-feed. Rank17/18 nominal gross (69,915 / 61,047 USD) likewise sits in same-block captures. Rank16/19/20+ step-2 slowness and the ranks11–15 funding batch (step 1b) remain. **No ranks15/17/18 taker classifies slow (median ≥10 s); step3 candidates stay zero.**


## Candidates (step 3)

None selected. The corrected sample establishes no slow Base Morpho operator and no slow ethereum operator (ranks2/3/6/7 fast 2026-11-14; ranks11/13/14 fast and rank12 intermediate 2026-11-14; ranks15/17/18 fast 2026-11-14 run 329ef7a8). Need slow operators (median >=10s) taking >=half of >=$300 **window effective market gross** (window: from 2026-10-26, ~18 days), with fast-first captures rare. Current missing history and unmeasured eligibility prohibit applying that rule. No Japanese completion report has been issued because steps 1–3 remain open.
