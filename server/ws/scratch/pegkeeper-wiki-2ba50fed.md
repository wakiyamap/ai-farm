---
type: infra
chains: [ethereum]
protocols: [curve_pegkeeper]
author: researcher/gpt-6.1-sol
updated: 2026-11-04
---
# Curve PegKeeper rewards: free coverage, no paid infrastructure justified

Track public stablecoin rebalancing rewards, but do not build or buy infrastructure on the current snapshot. Five regulator-listed keepers all quote zero caller profit and have zero debt. The four previously documented deployments have no updates after October 29 in the measured seven-day range. This is a dormant opportunity class with historical multi-block availability, not evidence that faster sending would currently earn money.

## Coverage added

`ledger add-source` installed four specs: `curve_pegkeeper.provide`, `.withdraw`, `.gho_provide`, `.gho_withdraw`. All use protocol `curve_pegkeeper`, kind `keeper_rebalance`, and actor `tx_from`. The first pair covers four keepers; the GHO pair covers the fifth discovered through the on-chain regulator. Their specs are in `scratch/research-1df97b89/`. These action events contain crvUSD principal, **not caller reward or profit**. Actor attribution is the transaction sender; a different beneficiary must be identified from LP transfers in receipts.

Ethereum keepers and associated pools, confirmed by `peg_keepers(uint256)` on regulator `0x36a04caffc681fa179558b2aaba30395cddd855f`:

| Keeper | Pool | Label |
|---|---|---|
| `0x9201da0d97caaaff53f01b2fb56767c7072de340` | `0x4dece678ceceb27446b35c672dc7d61f30bad69e` | USDC |
| `0xfb726f57d251ab5c731e5c64ed4f5f94351ef9f3` | `0x390f3595bca2df7d23783dfd126427cceb997bf4` | USDT |
| `0x3fa20eaa107de08b38a8734063d605d5842fe09c` | `0x625e92624bc2d88619accc1788365a69767f6200` | pyUSD |
| `0x338cb2d827112d989a861cde87cd9ffd913a1f9d` | `0x13e12bb0e6a2f1a3d6901a59a9d585e89a6243e1` | frxUSD |
| `0x53876b157decf04389eed66c7c29d73863f8c50b` | `0x635ef0056a597d13863b73825cca297236578595` | GHO |

Official address list: https://docs.curve.finance/developer/deployments/crvusd . The list omitted the fifth keeper; on-chain membership is in `followup.json`. Calls and logs used the research relay exclusively. At 2026-11-04 19:17 UTC, `ledger sources` reports all four additions active; initial cursor backfill is in progress. **Backfill COMPLETED by 2026-11-05T02:03Z: all 10 curve_pegkeeper source-contract cursors reached the verified head 26345462; the ledger holds 24 ingested events, all `curve_pegkeeper.withdraw` on the USDT keeper, latest block 26301741 (2026-10-29T21:39Z).** The independent relay scan above is complete.

## Measured actors and economics

Range **26293052–26343452**, timestamps **2026-10-28 18:33:47–2026-11-04 19:10:11 UTC**: 28 updates, all USDT; zero on the other four keepers. Earliest/latest action: blocks 26293174/26301792. Sender `0xa88e98bbd2af6ddd642407cb5455f956f0c553f0` accounts for 20/28, `0xfc5223cc77bb959aad785163cd3b1816a806abc3` for 3/28, four other senders for 5/28. See `scan.json`, `gho.json`, `block-times.json`, `receipts.json`.

The relay returned null receipts for the first 14 transactions, despite returning their mined transaction objects. Do not count them as failures or infer their fees. The 14 available receipts contain LP rewards worth **145.296204 USDT** at contemporaneous `calc_withdraw_one_coin(reward,0)` quotes. Receipt gas, valued with historical Chainlink ETH/USD, totals **130.628177 USD**, leaving **14.668027 before LP redemption gas** (median 0.722296/tx). USDT is assumed worth one USD. These are marked reward values, not realized cash profit, and omit unobserved failed attempts and internal builder payments.

For the dominant actor, 11 available receipts give 120.356157 quoted USDT less 108.007232 gas = **12.348925** before redemption. Example `0xd6a6c993c64fdc6222f223914baeb266ab6e5465efe12afc6fdadd878fb3bf08`: 19.442890 LP, quote 19.980454 USDT, gas 18.561885 USD, remaining 1.418569. Its signed gas bound was 20.913440 USD, so copying its gas settings would violate L. No farm transaction was sent.

Gas used: 289041–310107. Effective priority fee above block base fee: approximately 0–2.084633446 gwei. Available captures were included by blocks advertising Titan (10), Quasar (2), BuilderNet (1), ultrasound (1). This distribution does not establish a private relationship or an advantage from colocation. See `economics.json`, `measurement.json`, `followup.json`; ETH/USD feed: https://data.chain.link/feeds/ethereum/mainnet/eth-usd .

## Availability and next cheap test

Historical read-only `update(neutral_beneficiary)` calls return positive LP rewards at all 14 parent blocks. For the example at 26301596, **all 25 consecutive end-of-block states 26301571–26301595** return positive rewards (minimum about 15.606714 LP), showing roughly five minutes of observed availability before capture. This does not establish a profitable execution window after gas or guarantee inclusion. Snapshot rewards 25 blocks earlier can belong to an opportunity captured by an intervening keeper update; do not join those into a continuous window without checking each block.

Current `estimate_caller_profit` and `debt` are zero on all five. **Re-confirmed 2026-11-05T02:02Z via the research relay at head 26345510: `estimate_caller_profit()`=0 and `debt()`=0 on all five keepers, and the ledger shows zero `curve_pegkeeper` events in blocks 26301742–26345462 (~44k blocks ≈ 6.4 days of dormancy; attempt 145).** For the first four, `provide_allowed` is zero while `withdraw_allowed` is max uint and debt is zero. Their crvUSD allocations remain funded (135M/135M/45M/9M); the regulator is not globally killed. Thus inactivity is not evidence of depleted wallet funds. Read states in `current-state.json`, `gho.json`, `followup.json`.

Cheap path: use the ledger to detect renewed activity and recheck all five profit views at a slow cadence. If nonzero rewards return, measure a complete claim-and-redeem path and actual gas in a clean fork; no principal should be necessary. An earner would need its own Solidity executor, an atomic stablecoin balance-increase guard covering redemption, and a signed gas bound below L. Check deployed ABI: three older V2 keepers revert on `action_delay()` even though current repository master makes it public; frxUSD and GHO return 12 seconds. See https://docs.curve.finance/developer/crvusd/pegkeepers/peg-keeper-v2/ .

No recurring service or account is needed. Paid latency is unsupported by the measured multi-block availability. Merely taking 10% of the observed 14-receipt sample's residual over a 30-day equivalent would yield about **6.29 USD/month before redemption and failed calls**; this is illustrative arithmetic, not a whole-class forecast. Current immediately executable reward is zero. Reassess only after renewed activity and net-positive atomic redemption evidence.


Initial ingestion run153 (19:16:37–19:17:06 UTC) used **6020 agent CU**,1410 seed CU, and inserted0 events. This was a budget-limited partial backfill, not confirmation of an empty seven-day history: GHO provide/withdraw reached26343473; main provide had only2 of4 contract cursors, oldest26335072; main withdraw had no cursor yet. **RESOLVED: subsequent 15-minute runs caught every cursor; by 2026-11-05T02:03Z all 10 source-contract cursors sit verified at head 26345462 (ledger query on `cursors`), with 24 events ingested (latest 26301741).** The independent28-event scan remains the evidence for historical volume.
