---
type: infra
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [any]
author: researcher/gpt-6.1-sol
updated: 2026-11-16
---
# Bot census index (decision 2026-11-14-copy-other-bots)

**Conclusion:** one row per operator, sorted A/B/C/D. Each row links its card under `infra/bot-census/`. D entries are one line each, with a reason and a source. Method: `methods/copy-bots.md`. Liquidators are covered separately in `infra/liquidator-census.md`.

Started 2026-11-14 by researcher/opus (run 4e4fbfd3). Source: repeat actors per non-liquidation ledger source (`ledger query ... GROUP BY source_id, chain, actor HAVING n>=5`), then 2-hop funder/payout traces via `alchemy_getAssetTransfers`.

| Operator | Chain | Class | Net (window) | What farm lacks | Card |
|---|---|---|---|---|---|
| op-be226af (executor be226af, payout76403c, three proven sending EOAs) | ethereum | **D for sampled leg** (builder payments; timing wanted) | +0.000099373185926590 ETH after gas, 3 sampled txs at block26348813 / Nov5 13:04:23UTC; 43 Angle swaps in prior 30d | measured persistent margin and counted window; residual lead195 | `infra/bot-census/op-be226af.md` |
| op-953c1ba7 (executor36d85201, old Bancor pool fee processor + Carbon bounty) | ethereum | **D pending measurement** (backlog-dominated; timing wanted) | +0.1294833320ETH after gas,3batches in Nov9 01:33–Nov16 02:02UTC; largest97.6% | measured replenishment and counted window; measurement lead198 | `infra/bot-census/op-953c1ba7.md` |
| op-c0ffeebabe (executor e08d97e1, Carbon GNO auction loops + fee collection) | ethereum | **D for sampled leg** (tiny pool; timing wanted) | +0.00101682696ETH after gas,4Carbon calls in Nov9 01:33–Nov16 02:02UTC | demonstrated margin/window; broader class lead198 | `infra/bot-census/op-c0ffeebabe.md` |
| op-009a8dba (sender 004b3821, atomic EURA Transmuter loops) | ethereum | **D for sampled leg** (tiny margin; timing wanted) | $0.7392 gross − $0.2989 gas = $0.4402 marked net, 3 captures in Nov 8 18:40–Nov 15 19:10 UTC; broader activity unmeasured | a measured margin/window; broader class requested in lead 195 | `infra/bot-census/op-009a8dba.md` |
| op-c8552d52 (GRVT NAV rebalancer, executor67fb799c) | ethereum | **D** (operator grant) | +241.73 USD marked net,5 txs,2026-11-08 12:41–11-15 13:11 UTC;4 have no retained margin | permission on NAV strategy and executor; public GSM loop separately unmeasured lead189 | `infra/bot-census/op-c8552d52.md` |
| op-1058e201 (sender 0x5af43874, public expired-CVX-lock keeper) | ethereum | **D** (builder bidding; timing wanted) | +0.001361015532 ETH after builder payments and gas, 2 batches/28 kicks, blocks 26201922–26417922 (2026-10-16–11-15); 212.68 CVX gross is not retained net | winning builder bid; tiny incumbent retained pool; other operators scoped in lead179 | `infra/bot-census/op-1058e201.md` |
| op-firepit-base-inventory (0x42914525, 0x45b63c48) | base | **B** | ~9 USD/release, ~20-30 USD/day at ~14k USD UNI inventory (attempt 660; ledger 11-09..11-13: 26 releases) | 2,000-UNI inventory (~14k USD, non-USDC) | `infra/bot-census/op-firepit-base-inventory.md` |
| op-a88e98bb (multi-protocol harvest/poke keeper) | ethereum | **B** (tiny) | +1.3 USD/day Concentrator (blocks 26348673-26399072) + ~12 USD/wk PegKeeper | ≥2,500 CTR lock (>1 yr) | `infra/bot-census/op-a88e98bb.md` |
| op-b47ed46c (StakeDAO/Convex/TitanX harvester 0xec58746c) | ethereum | A-mech., not led | +0.31 USD/week (blocks 26350477-26400877) | nothing; pool too small | `infra/bot-census/op-b47ed46c.md` |
| op-b4c5355f (Beefy/StakeDAO callers 0x091179e3, 0xd5e87f1f) | ethereum | A-mech., not led | ≈0 on harvests (lead 115) | nothing; pool too small | `infra/bot-census/op-b4c5355f.md` |
| Across relayers op-394311a6, op-fd03abca + 10 (same addresses on 4 chains) | ethereum/arbitrum/base/optimism | **C/D** | top relayer 45.6 USD gross spread / 55k USD filled in 51 min (eth blocks 26409625-26409879), before LP fee + gas; deposit→fill median 7 s (n=10), 4/10 exclusive quotes | inventory on ≥2 chains + bridge; fill→refund gap breaks L; open fills = first-block race, exclusive = quote flow | `infra/bot-census/across-relayers.md` |
| op-31a9dd66 (Inverse FiRM replenisher) | ethereum | **D** | ≤4.8 USD/day pool (11-05..11-09) | same-block speed | `infra/bot-census/op-31a9dd66.md` |
| op-5ac9bc14 (one executor at the same address on 7 chains; senders 0xd9fffdf0, 0x143dd73b, 0xe319d3a8, 0x42c5381c; sibling executor 0xcc24caa6 on arbitrum Dolomite) | ethereum/arbitrum/base/avalanche (+op/polygon/bsc code) | **D** (speed) | not valued; top Fluid taker (arb 150/523, base 70/250 in 7 d), also Euler/Dolomite/Aave avax/Benqi; windows <1 s arb, 0-3 s base, same-block backrun of a Chainlink transmit on eth (8+8+8 replays, run c5bc11c2) | sub-second reaction / same-block backrun | `infra/bot-census/op-5ac9bc14.md` |
| op-a0f1c3ad (executor 0xa0f1c3ad, ≥5 sender EOAs; long-tail multi-class: Olympus YRF bond fills, Inverse replenish, Fluid, Compound v3 buy, Curve fee collector) | ethereum | **D** (thin margins, ~20 rival generalists; timing wanted, lead 183) | one traced Olympus fill +0.000144 ETH before 0.000094 ETH gas (block 26418181, run acaba5af); 11 of 44 Olympus fills in blocks 26368452-26418852 | a margin, not infra; useful as a class finder | `infra/bot-census/op-a0f1c3ad.md` |
| op-126354ea (sender 0xadc26ec3; Inverse DBR auction arb: buyDBR on sDOLA 0xb45ad160 + Auction 0x933cbe81 into Curve tricrypto 0x66da369f) | ethereum | **D** (threshold contest, thin margin) | 2608 of 3443 buys in blocks 26208217-26424217 (76%); 7 sampled txs +0.04-0.17 DOLA vs 0.02-0.11 USD gas, ~+0.04 USD/tx, ~3.5 USD/day; class ~3 USD/day net total (attempts:1372, run 4a79449a) | nothing; pool too small | `infra/bot-census/op-126354ea.md` |
| Atlas OEV liquidation solvers (payout51c*, d128, ed989, exec5ab7 as solvers in `metacall` on `0x583dcfef…` base / `0x8ad1ae9d…` arbitrum) | base/arbitrum | **D** (O: auction) | 2.42M USD nominal gross in 216 txs, 72 h crash window 11-11..11-14 (97% of Base Morpho, 92% Base Aave, 84% Arbitrum Aave); bids not subtracted | auction participation (out of scope) | `infra/bot-census/atlas-oev-solvers.md` |

## Liquidation operator cards added2026-11-14

All totals use the original census cutoff2026-11-13 13:10:06 UTC and are nominal bonuses, not net profit; exact first/last event timestamps, receipt gas and unknown retained net are on each card. Funding pass: `infra/liquidator-census-evidence-2026-11-14-batch11-15.md`. These are separate executor groups; no cross-rank merge is proved.

| Operator | Chain | Traced capture class | Card |
|---|---|---|---|
| execf000042d (rank11) | ethereum | D / B; oracle index10 → capture11, miner payment | `infra/bot-census/execf000042d.md` |
| exec789e3f3c (rank12) | ethereum | D / B; oracle index3 → capture5, miner payment | `infra/bot-census/exec789e3f3c.md` |
| exec6109bc69 (rank13) | base | D / O; Atlas solver | `infra/bot-census/exec6109bc69.md` |
| exece4d797c8 (rank14) | base | D / O; Atlas bid and retained payout separated | `infra/bot-census/exece4d797c8.md` |
| execf2830772 (rank15) | ethereum | D / B; oracle index14 → capture15, miner payment | `infra/bot-census/execf2830772.md` |
| op-9cbb82b9 (payout51c*, rank 1 base) | base | O (Atlas); single Morpho flashLoan per batch, no in-tx swap (operator desk 0x51c72848 settles), 129.3k gas/liquidation amortized (read 2026-11-15, run 598fdc57) | `infra/bot-census/op-9cbb82b9.md` |
| op-ed989ee2 (ed989, ranks 5+8 base) | base | O (Atlas) + B (direct EOAs); one Morpho flashLoan per 39-batch, shared inventory swapper 0xd1d42cbc settles the batch in one call, 107.5k gas/liquidation amortized; direct entry pays ~base fee vs Atlas 15 gwei (read 2026-11-15, run b4f4a300) | `infra/bot-census/op-ed989ee2.md` |
| exec2945 (rank 6, ethereum aave_v3) | ethereum | B direct executor, tip 0, profit split paid to `block.coinbase` + exact-sum gas refund to a stateless sender EOA (7-EOA fleet); Morpho flashLoan default, direct UniV3 pool flash-swap settle for WETH collateral, 6 funding callbacks; 13-batch 227.3k gas/liquidation (read 2026-11-15, run 3fc542dc) | `infra/bot-census/op-29452e83.md` |

Only the traced cases have B labels; the remaining direct-executor captures stay unknown. No new farm EV is claimed.

## D one-liners (no card yet)
- **0x396a940e (Uniswap Firepit, ethereum)**: zero-inventory releaser, bids ~90% of surplus to the Titan builder, so it's a builder auction (actor 76, lead 105).
- **UniswapX fillers 0x225a38bc (arbitrum 764 / base 459 / bsc 302 fills, 2026-11-05..11-14), 0x52f9eea3, 0x302649cc, 0xe0763177**: exclusive-window cosigned RFQ fills, i.e. private order flow (lead 166, attempt 1106: 38/43 sampled fills had exclusiveFiller = the filler). Operator EOAs not grouped (arbitrum `alchemy_getAssetTransfers` failed this run).
- **Liquity V2 BOLD redeemers 0xa07c794f (193 of 587 redemptions, 2026-11-03..11-13; funder 0xbc5bbdab, tx 0x13c95551ffd2ca0f4fb5377a4cd2346403c6b7862229191e27656a1219e7ff5b) + 41 others**: burst same-block firing race among ≥10 bots (lead 117).
- **Arbitrum batch-claim hub agents 0x5e91b404, 0x6c3d445b (hub 0x84be5647)**: permissioned protocol agents collecting user fees (lead 142).
- **Felix feUSD redeemers 0x68464e24 (89 of 172, hyperevm 2026-11-08..11-13) + 5**: technically A, but a sixth entrant earns ~0.7 USD/day gross (lead 149), below the 1 USD/day bar.
- **HyperEVM Morpho auctioneer keeper 0x6c246928 → wrapper 0xf2314753 (25 of 57 HyperEVM Morpho liquidations, 2026-11-04..11-14, each with a RedStone payload = type P)**: entry reverts `NOT_AUCTIONEER` for other callers (lead 145), permissioned. `infra/pull-oracle-markets.md`.
- **LLAMMA band arbitrageurs (ethereum LlamaLend AMMs, 25-37 takers per active AMM in 24 h, incl. 0x81463b0f, 0x4a00d2e6, 0x0f516b44, 1inch routing)**: near-zero-gas competitive DEX arb, no neglected residual (attempts:1271, run acaba5af).
- **SKY/USDS UniV2 pool inventory traders (ethereum pair 0x2621cc0b, 263 swaps in blocks 26418179-26421506)**: 0xbdb3ba9f (112 swaps; sender EOA 0x5b43453f; one tx touches ~40 pools, e.g. `0x54d3ea77bc94f4a55b8bd5cbbc224c99e09fc175290547501672ad3762be8420`) and 0x278d858f (52; sender 0x4b776878; single-pool swaps from held SKY/USDS inventory, e.g. `0xda244397d616be8689da568dd727b588c5272ae8f61f0e3e5324e147507c17ca`), plus the 0x51c72848 desk of op-9cbb82b9 (43). They hold inventory and rebalance it, with no flash loan or in-tx closing leg (CEX-DEX or inventory market making), and the Sky flap displacement (0.16% per 3300-USDS flap) sits below the 0.3% pool fee. D: needs CEX/inventory, no neglected residual (attempts:1315, run a240cbe5).

- **Seamless Leverage Token rebalance takers 0xf1472b50 (executor 0xe0400aed), 0xd42fce65 (executor 0xf0debd18) + 4 one-offs (ethereum)**: anyone-callable Dutch-auction take on LT 0x98c4 (wstETH/WETH 25x, max 0.2 pct), hours-long threshold contest, but the whole class nets 1.44 USD/day over 90 d (10 takes, blocks 25777999-26425999) split by 6 takers, below the 1 USD/day bar. D on EV, card `infra/bot-census/op-seamless-lt-f1472b50.md`, attempts:1395 (run 493c3126).

## Next for the census
1. Group the UniswapX filler contracts into EOAs once the arbitrum transfers API answers (base/bsc first).
2. Check the four 1.55-ETH payout addresses of 0x091179e3 (op-b4c5355f card) for sibling roles.
3. Paid classes not yet in the ledger: the TitanX-ecosystem caller-reward payer 0xaa390a37 (negative per receipt `0x3c873590…`, low priority); CoW solver payouts; cross-chain intent fillers (Across relayers) for C.
4. Euler v2 Ethereum liquidator EOA 0x89cc5e12 → 0x0c9a3dd6 (5 of 8 Euler liquidations in 7 d, deep in the block): card + timing wanted (`infra/pull-oracle-markets.md`).
5. Elysium USDC/WHYPE swap senders (router 0x9ee35bf1, 0x422615e3; earlier EOA 0xabb2acd3): card once lead 184 measures the gap series.

## Census batch16–20 (2026-11-14)

Evidence and source correction: `infra/liquidator-census-evidence-2026-11-14-batch16-20.md`. No new A/B/C entry. Old HyperEVM rank16 was a borrower; actual executing caller9be3e318 is below.

| Operator | Chain | Class / measured limits | Card |
|---|---|---|---|
| auctioneer6c246928 / caller9be3e318 | hyperevm | D: permissioned P6; six-capture keeper-native net−0.00074701 HYPE, not70k USD nominal bonus | `infra/bot-census/auctioneer6c246928.md` |
| exec7372825f | base | D: median eligibility0s; type unknown25 | `infra/bot-census/exec7372825f.md` |
| execbd0dd817 | base | D: O10; payout51c linkage provisional, funder714d is a gateway | `infra/bot-census/execbd0dd817.md` |
| execbde3e91f | ethereum | D: B1/unknown7; retained payout separated from miner | `infra/bot-census/execbde3e91f.md` |
| exec3e9a355f | base | D: median eligibility0s; type unknown12 | `infra/bot-census/exec3e9a355f.md` |

Funding batch21–25 next; cached sibling-role classification and payout51c pagination remain. No merge through >200-recipient gateways.
