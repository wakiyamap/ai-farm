---
type: infra
chains: [ethereum]
protocols: [angle_transmuter]
author: researcher/gpt-6.1-sol
updated: 2026-11-16
---
# Bot census: executor be226af — flash-funded EURA peg loops

**D for the sampled route: three consecutive arbitrages pay the builder and retain only 0.000099373185926590 ETH after sender gas in block 26348813 (2026-11-05 13:04:23 UTC). Timing wanted; no countable farm EV established.** Lead 195 requests only the remaining flash-size evidence gap. No bot is recommended from these samples.

Executor `0x0000000000be226afde21672a5e4adc45692e69d`; common payout `0x000000000076403c099f98973a39018fe4ff2343`. Three different sending EOAs are linked by calls to this executor and its same-transaction payouts, not by coinbase transfers:

| Capture | Sender | ETH paid to payout | Sender gas ETH |
|---|---|---:|---:|
| `0xfb1c9673074231e48d4b6d543962406f7daf21254264b9fb4a91d675b9ed1d6f` | `0x0000000000382d3e66faf4f7c563b76b2da40f98` | 0.000205722035266141 | 0.000147057786446198 |
| `0xd92acc8d2ddb25e19dab92ae82cc6683baf8fc89e4c052b1cddd029aa33d97c2` | `0x00000000004b113df868ef8d3082db47d3389dd2` | 0.000176714295270444 | 0.000145674495280694 |
| `0x6036814ad1a170269c2efb08d8f9dd65a8ca35b1b33af48ceac295c39f026d2e` | `0x00000000008687b5a345d987be1ece8dd0954d0e` | 0.000166100655606277 | 0.000156431518489380 |

Windowed total: three sampled transactions at indices 48–50 of that one block, payout 0.000548536986142862 ETH, gas 0.000449163800216272 ETH, native cash net 0.000099373185926590 ETH. Builder payments total 0.001056876360897574 ETH, to the block's independently verified miner `0x4838b106fce9647bdf1e7877bf73ce8b0bad5f97`. One transaction also carries unrelated routed USDC/native flows; these figures are complete-transaction retained cash, not isolated Angle spread. Do not extrapolate this three-case sample into daily revenue. USD historical valuation and full operator income are unmeasured.

The cached 31.6325-day residual scan (blocks 26194355–26421380) has **43** Angle swaps by this executor, all no later than 26348813. Amounts are principal, not profit. The sampled advance is **1117.847849 EURC**, not millions of USD. Flash funding removes the wallet-capital objection; a final farm executor would still need to settle in native or USDC and enforce its profit guard. No second-chain inventory is seen.

## Contract and trigger

Complete callTracer shows a flash advance at `0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb`, EURC approval and mint through official EURA Transmuter `0x00253582b2a3FE112feEC532221d9708c64cEFAb`, Curve pool `0x413928a25d6ea1a26f2625d633207755f67bf97c`, Uniswap pools, flash repayment, sale of residual EURA into WETH, unwrap, miner payment and common payout. The route uses helper `0x00000000008b28947753a8e8aea9933d2298eda6`; no verified executor source is claimed. The trigger is a favorable complete peg loop, not a protocol-paid keeper bounty. Entry selectors are opaque; this is an observed mechanism, not a ready ABI.

Timing is **wanted**. Cases per timing type: three unknown, all with explicit miner payment; builder access explains bidding but does not by itself prove B (oracle backrun) or a latency window. Farm lacks a demonstrated persistent margin and a counted window under Ethereum R=12 s. Private send alone does not supply builder bidding or make these captures count.

## Funding and payout boundary

First sender's earliest returned external funding: `0x6fc765367cb0368081d244a76a15f77b4b367f09` → sender, tx `0x971e5745d780e0abd53e14d19312c575cabaea30704081ff987f5e5d66ee3f8d`. Hop two: `0xc835c4d7a28e101f611581fe135d12282931a04a` → funder, tx `0x14624ca7ad9016a3e56570276cbff4b96b6487639efd1c201347d2bb06f8e59e`. Funder's complete returned external page has 211 transfers to 107 recipients; their roles are unclassified, so no 107-sibling claim. This is one funding branch, not proof of a complete funding graph for all three EOAs.

Payout → `0x000000000047c83ce4365e5d513ecc9f7904464e`, tx `0xa6d28c91bfa2738cd13e1fb27aa4c9e3b350fbca413c2633657831b6eb2d5ba8`. This recipient's external outflow query returns zero; internal/token categories have not been exhausted. No owner identity or further operator merge is inferred.

## Accounting pitfall

EUROe frontend `0x3231cb76718cdef2155fc47b5286d82e6eda273f` and backend `0x39b8b6385416f4ca36a20319f70d28621895279d` represent the same token storage. A route can receive using the frontend and repay using the backend, leaving a fake positive frontend-only Transfer sum. Explorer-verified EUR.sol transfer/transferFrom forward to the controller and emit a frontend event. The existing operator's control tx `0x4ffc775c2df6a8ad5850f5a32b8387a33d05835d3f9c91ed151422a3b72d04a1` has an apparent +1000.972547 frontend-token delta, while balanceOf(executor) is zero on BOTH interfaces at blocks 26348449 and 26348450. This is not profit and is not a contract flaw; merge interfaces or verify balances.

Evidence: `scratch/angle-residual-logs.json`; `scratch/research-b299/{samples,decoded}.json`, `0..5-{receipt,trace}.json`, `be-block.json`, `e08d-block.json`, funding/payout files, `token3231/EUR.sol` and `balance-*.json`. All chain reads use the research relay. No sends, fork or bot work.

Window duration correction: relay header timestamps for blocks 26194355 and 26421380 are 2026-10-15 00:33:23 and 2026-11-15 15:44:11 UTC: **31.6325 days**, not exactly 30. Use this duration for any rate; do not divide this historical window by 30. Headers: `scratch/research-b299/window-{start,end}.json`.
