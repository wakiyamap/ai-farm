---
type: infra
chains: [ethereum]
protocols: [aave_v3, compound_v2, compound_v3, sparklend, morpho_blue, uniswap_v3]
author: earner/qwen3.8-flash-next
updated: 2026-11-15
---
# Bot census: op-bc034 (ethereum multi-protocol liquidator, Safe-style wrapper) — class B (behind the oracle update, zero tip)

**Conclusion:** bc034 executes every batch as ONE transaction: a thin wrapper (`0xd95c43e9`) delegatecalls an implementation (`0x2770bd8d…`) which runs 16 per-position sub-executor delegatecalls (`0x245d655e`, 372k-1887k gas each), each funding itself with a flash loan (Morpho Blue `flashLoan` ×15, Balancer Vault `unlock` ×23), taking one position (aave v3 `liquidationCall` ×10, compound v2 `absorb` ×6, plus Spark / compound v3 buys), exiting collateral through UniV3/Pancake v3 swaps (5 `swap` + pancakeV3SwapCallback), and repaying the loan; profit leaves as native to the operator EOA in the same tx. Gas 11,702,145 for the batch (~1.17M/liquidation) at effective gas price 0.3938 gwei = **priority fee 0** (gas 16.59 USD at 3,600 USD/ETH). Evidence tx `0x1b99cd15dd3e57403ce6ac8694a5568b1b6cdcff6f70dd08ee7e1735dcf530f4` (block 26415746, 10 aave liquidation events + more).

## Operator
- Executor `0xbc034f2327b1d2fc51fe9e197dbc35c17f592672` (census rank 3); implementation (delegatecall target) `0x2770bd8d2591cde7158725b4b3320e3e501848cd`; relayer/sender EOA `0x5168763828548020027232e15668d1cfebbe982f`; profit recipient = the same EOA (final CALL in the tx, after 16x WETH `withdraw`).
- Crash-window role: 68% of aave_v3 ethereum A gross, 89% of morpho_blue ethereum A gross (attempt 1185 / crash page taker table); sampled 1-3 positions sit 1-3 txs behind an `AnswerUpdated` tx with tip 0 -> type B (or O, same-block backrun), not a latency class farm can out-race.

## What it does (traced, `scratch/c21b/trace_bc034.json`)
- Entry: one selector `0xd95c43e9` with 45,477-byte input (whole batch plan as calldata); only the operator EOA seen calling.
- Loop shape per position: `STATICCALL balanceOf(token)` snapshot -> `DELEGATECALL` sub-executor -> inside: flash loan -> protocol liquidate/buy -> swap (only when needed; direct token reuse otherwise) -> repay loan. A final `STATICCALL` WETH `balanceOf` and native transfer close the batch (balance-snapshot guard shape).
- Protocols in one batch: aave v3 pool `0x87870bca3f…` (`liquidationCall 0x00a718a9` x10 + one `flashLoanSimple` + `userReserveInterestRate` reads), compound v2 new `absorb(address,address,address[]) 0xc3cecfd2` x6, Spark pool `0x72e95b89…`, compound v3 cWBTC comet `0x3afdc9bc…` (`borrowBalanceOf` reads x6).
- Funding: Morpho Blue `0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb` `flashLoan(address,uint256,bytes)` x15 (callback `onMorphoFlashLoan` x15) + Balancer Vault `0x000000000004444c5dc75cb358380d2e3de08a90` `unlock` x23 (`unlockCallback` x10); fees not measured.
- Exit: UniV3 `swap 0x128acb08` x5 + Pancake v3 callback; route in calldata (per-position), not fixed in the contract.

## Result (window)
- Crash 72 h: 17 aave/morpho captures, 723,779 USD nominal gross (crash page top-taker line). Retained net not measured; gas is paid by the operator EOA at tip 0.

## What farm lacks
- Nothing structural for a single-position clone; the batch shape needs a batch feed (many positions crossing per block), which farm's polling path could gather at crash speed. Timing (B, behind the oracle update with zero tip) is the blocker for copying, not the contract.

## Contract
- Read 2026-11-15 (earner run 071cd2ba, this page). Gas accounting inside the guard: unknown from callTracer (no visible `tx.gasprice` read; per-position balance snapshots seen). Techniques extracted to `methods/executor-techniques.md` rows 9-10. No mainnet tx sent to it; fork/relay reads only.
