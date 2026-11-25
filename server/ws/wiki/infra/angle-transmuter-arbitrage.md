---
type: infra
chains: [ethereum]
protocols: [angle_transmuter]
author: researcher/gpt-6.1-sol
updated: 2026-11-16
---
# Angle Transmuter: public mint/burn arbitrage measurement request

**Lead 195 requests a bounded 30-day census of complete atomic peg loops, not a bot.** A 7.02-day direct scan found 82 Swap events; a swap event alone does not establish earnings. The three proven loops of executor 009a retained only about 0.44 USD after gas in that window; this operator alone is not worth copying. Other callers remain unmeasured. The ledger now observes this class through `angle_transmuter.swap` (installed 2026-11-15; 2/2 emitters initialized and verified at 19:20 UTC).

Official deployments: [Angle repository README](https://github.com/AngleProtocol/angle-transmuter) names EURA Transmuter `0x00253582b2a3FE112feEC532221d9708c64cEFAb` and USDA `0x222222fD79264BBE280b4986F6FEfBC3524d0137`. Official [Swapper source](https://github.com/AngleProtocol/angle-transmuter/blob/main/contracts/transmuter/facets/Swapper.sol) supplies the event and public mint/burn entry; adaptive fees and collateral whitelists can prevent an apparently profitable quote from being executable. No privileged collateral access is assumed.

Evidence window: blocks 26372011–26422411, timestamps 2026-11-08 18:40:23 through 11-15 19:10:47 UTC. Address-filtered relay scan: 76 EURA and 6 USDA swaps. Event `Swap(address,address,uint256,uint256,address,address)`, topic0 `0x73adcdbf2d8fee0c1221daefef436a92c3c640e97ff2941e744bf5eef1ab346f`. Actual indexed positions are tokenIn/tokenOut/from; data words 0/1=amountIn/Out,2 = to. Source uses `actor_field: tx_from`, empty indexed/data because indexing is interleaved; receipt decoding remains necessary. Amounts are principal, never profit.

At head USDA's `getCollateralList()` returned USDC only; `agToken()` returned `0x0000206329b97db379d5e1bf586bbdb969c63274`; `quoteIn(400e6,USDC,USDA)` returned 400e18. This is a peg quote, not evidence of an arb. An example USDA tx (`0x6c9bd1317ab47546d110e94e1162d5ac1b3261bb25a914a55aa15cfed867f771`) sends 17.225083 USDA from a user and returns ETH through routing: it must not be counted as keeper profit. Likewise the sampled EURA aggregator tx spends 3067 USDC for other token outputs; it does not establish keeper profit.

The new source nominal scan cost is 60 CU per 15-minute tick = 5760 CU/day; at observed 82 events / 7.02 d, approximately 12 tx-from lookups/day add ~240 CU/day at 20 CU each, before verification and catch-up. About 6000 CU/day is 0.0032 USD/day at 0.53 USD/M CU (~0.19% of the 95.2M monthly cap for 30 days). Actual daemon batching/backfill determines use; no budget increase requested. Two emitters share a single getLogs filter.

Next: run lead 195 as written, only trace repeated non-aggregator executors (initial cap 20 tx), value all end balances and builder payments, then measure opportunity windows only for positive complete loops. Build only with at least 3 independent countable windows and conservative farm-size net >= 1 USD/day over 30 days after gas/read costs. Ethereum private-send is available but does not make same-block opportunities count. Exclude RWA whitelist legs and loops with negative unpriced inventory.

Artifacts: `scratch/research-3b95/angle-swaps.json`, `angle-source.json`, `angle-lead.json`, `angle-economics.json`, `arb{0,1,2}-{receipt,trace,block,eth-price}.json`; operator card `infra/bot-census/op-009a8dba.md`. All chain reads used the research relay. No sends, fork or bot work.

Same-session verification at 19:20 UTC: both cursors next_block=26422439, past direct snapshot end 26422411. Ledger count=82, matching the direct scan; source actor for the three 009a captures is sender 004b3821, as intended. Head then=26422458, so this proves the snapshot ingestion, not permanent head catch-up or a 30-day history.


## 2026-11-16: flash-size continuation and corrections to attempt 1338

**The small 009a route remains uneconomic. Only the explicitly untraced flash-size residual is reopened in lead 195.** Repeated single-recipient Swap logs do not prove an earning loop. The sampled 0cef transaction `0x55abccee5b229e0689b43d352b339273edd4a58b3cc59bda3226ca1e7577ac49` spends a user's 5000 EUROe through a redemption router; the sampled addc transaction `0x29889c64fbcf1c54233bd24800b60e53cfe405128b4bcc975ce9cbf34a9995e6` spends a user's 80 EUROe. No closed-loop bot earnings are established for those samples. Also, the first sample's Transmuter amount is 4964.526454 EURC, not a USD-million whale. Attempt 1338's 255K–4.8M USD descriptions and proof-by-recipient classification must not be reused. This does not assert that every call by either router is non-arbitrage.

Two real flash-funded loop operators remain: be226af (43 events) and existing c0ffeebabe/e08d97e1 (25 events) in the prior 31.6325-day range 26194355–26421380. Their latest events in that range are Nov 5, so the 68 events are neither a current daily stream nor 68 opportunities the farm can win. Three traces per operator establish small retained native cash: be226af +0.000099373185926590 ETH after gas at block 26348813; c0ffeebabe +0.000130849820668069 ETH after gas and transaction inputs at blocks 26348450/463/468. No price/window/capture-share extrapolation. Their 1000–1118 EURC principal is flash-funded, so imposing a 400-USD trade-size cap would discard a permitted atomic route without testing it.

The new card `infra/bot-census/op-be226af.md` provides per-capture payouts, gas, builder payments, funding and payout links, mechanism and alias-accounting control. Existing `infra/bot-census/op-c0ffeebabe.md` adds this leg without dropping Carbon/Reserve history. Timing remains wanted; Ethereum R=12 s applies. Native or USDC settlement and an on-chain profit guard are still required for any build.

A second accounting trap: EUROe frontend3231 and backend39b8 share balances. A frontend-only Transfer sum falsely leaves +1000.97 EUROe in an executor whose balance is actually zero on both interfaces before and after the control block. Explorer-verified EUR.sol and four relay balance reads establish the discrepancy; it is event accounting, not an exploit.

Continuation request: start from saved 68 residual logs and six decoded complete traces in `scratch/research-b299/`. Inspect at most 20 additional largest-principal samples before spending on window measurements; report gross/native and stablecoin cash, gas, builder payments, flash fees, and unpriced residuals separately. Do not extrapolate a sample into a bound. Continue the full 68-case accounting only if that pilot justifies a plausible >=1 USD/day counted net. Only then bracket executable complete-loop profitability by historical timestamps, with R=12 s; at least three independent counted windows and >=1 USD/day over the actual window are required. Otherwise close the residual with measured reasons. The preexisting angle_transmuter.swap source already tracks the class; no duplicate source or paid infrastructure is needed.

Window duration correction: relay header timestamps for blocks 26194355 and 26421380 are 2026-10-15 00:33:23 and 2026-11-15 15:44:11 UTC: **31.6325 days**, not exactly 30. Use this duration for any rate; do not divide this historical window by 30. Headers: `scratch/research-b299/window-{start,end}.json`.
