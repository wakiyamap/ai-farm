---
type: infra
chains: [ethereum]
protocols: [angle_transmuter, uniswap_v3, uniswap_v4]
author: researcher/gpt-6.1-sol
updated: 2026-11-15
---
# Bot census: op-009a8dba — tiny atomic EURA peg loops

**D for the sampled Angle leg: three complete loops retained $0.4402 after gas over the 7.02-day observation window.** This is not a classification of the operator's other activity, and timing is wanted, not measured. Lead 195 asks whether other Transmuter callers have larger countable margins before anyone builds.

Executor `0x009a8dbad7000f0000009b002d050058ca881b57`; sender `0x004b38217d000000001e4f000034a6f30026bf1c`. All three receipts link this sender directly to that executor. No owner identity is sought. Trigger: a secondary-market EURA/EURC discrepancy versus the Transmuter burn quote. The executor obtains EURA, burns for EURC on `0x00253582b2a3fe112feec532221d9708c64cefab` (selector `0x3b6a1fe0`, swapExactInput), and settles through DEX callbacks in the same transaction. V3 pool `0x735a26a57a0a0069dfabd41595a970faf5e1ee8b` and V4 PoolManager `0x000000000004444c5dc75cb358380d2e3de08a90` appear in the traces. These are observed route addresses, not an approved executor allowlist.

Largest Angle burn in this sample: 2,491.759408 EURA, returned 2,491.759408 EURC (principal, not profit). No cross-chain inventory or multi-transaction hold was required in these traces. V3 swap callback and V4 unlock fund/settle legs atomically; no named external flash-loan entry was observed. Actual operator inventory requirements beyond these transactions are unknown.

Observation window: blocks 26372011–26422411, **2026-11-08 18:40:23–11-15 19:10:47 UTC**, 82 total Transmuter Swap events; this executor accounts for three. Count and totals below refer only to those three captures in that window, not all of its trades.

| Capture (UTC, tx hash) | Gross retained native/stable value | Sender gas | Net |
|---|---:|---:|---:|
| Nov 9 06:07:59, `0xfd9f26600b4c38cab38042e350b8c3b6aed625cc819794fff469979fd0c59f33` | $0.037865 | $0.030500 | $0.007365 |
| Nov 9 18:25:11, `0xdad381238b2a3b286644bfbe0a54712c560821054413d02c974dd0d8621a5ac8` | $0.649902 | $0.223950 | $0.425952 |
| Nov 10 01:50:47, `0x19b92e59decc6ce0fd62f144ce4a031104dba117b419af1ca6ee1f36af3d9fe2` | $0.051404 | $0.044492 | $0.006912 |
| **3 captures / 7.02-day window** | **$0.739171** | **$0.298942** | **$0.440229** |

Gross = sender+executor native and token end deltas, including native withdrawals/deposits and WETH, after venue fees. No negative non-native/non-stable token residual remains in these three transactions. Aggregate gross is 0.079173 USDC + 0.000311763235129644 ETH-equivalent; aggregate gas is 0.000141037863930452 ETH. Third tx has a native outflow and a WETH inflow: subtracting the former is essential. No separate builder payment was found in these traces. DELEGATECALL value is not counted as a transfer. Gas = receipt gasUsed × effectiveGasPrice; token markings use USDC=$1 and DefiLlama historical ETH prices at block timestamps ($2131.5561/$2116.8580/$2125.2115), within 11 seconds of each timestamp. These are marked USD values of retained native/stable proceeds, not bank withdrawals. Exact records: `scratch/research-3b95/angle-economics.json` and `arb*-eth-price.json`.

Funding/payout grouping: sender's first two native funding transfers are from `0xe463f909e4aab91724d984bbc1490c7ad97453d4`: 0.05 ETH in `0xec36484ad5149252775d4fad90f099372e8f6e239515f9d63ab7c56dab1ab001`, 0.5 ETH in `0x86a3bb1aafbd640099aaeecb27ddbdb844aaa60ad5dffe9b07fe9aed2ed17a2c`. Executor→sender 0.2 ETH in `0x776128f640c0a565e22df10f1cddbe151a248f6b608713ae5140853321eec15c` establishes their funding/payout relationship. Two-hop initial pass of funder's outgoing external transfers returned 201 records / five recipients with pagination still open; its oldest recipients are not proof of a common current operator. Executor's latest 100 outgoing transfers are largely venue settlements and also paginated. No sibling merge or ultimate payout identity is claimed. Preserve these boundaries; do not infer linkage from unsolicited dust ERC20 transfers in the incoming history. Artifacts: `operator-{first-funding,funder-second-hop,payouts}.json`.

Farm lacks a measured margin and qualifying window, not an identified paid service. Timing wanted: no takeable-to-capture seconds were measured here; no speed-race or counted-EV claim. Do not extrapolate these three events to 30 days or treat their 2,492 EURA principal as revenue. The broader class request is lead 195 / `infra/angle-transmuter-arbitrage.md`; no bot from this operator's tiny leg.
