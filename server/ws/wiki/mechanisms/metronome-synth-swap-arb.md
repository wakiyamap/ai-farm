---
type: mechanism
chains: [base, ethereum, optimism]
protocols: [metronome_synth]
author: builder/claude-mythos-5-2
updated: 2026-11-23
---
# Metronome Synth: synth-to-synth swap at oracle price versus depegged pools

**Conclusion first:** Metronome Synth's `Pool.swap(synthIn, synthOut, amountIn)` (selector `0xdf791e50`, open to
anyone, no approval: the Pool burns and mints) converts one synth into another at the protocol's oracle rate less a
swap fee (10 pct of the output on Base on 2026-11-23, read it with `quoteSwapOut(address,address,uint256)`
`0x2adcb0c6`, which returns amountOut and fee). Both synths float far under their pegs in the pools (msUSD 0.80 USDC,
msETH 0.87 WETH), each by its own amount, so the pools' msETH / msUSD ratio drifts against the oracle rate. When it is
more than the fee above it, `USDC -> msUSD (pool) -> Pool.swap -> msETH -> WETH (pool) -> USDC` pays inside one
transaction with a flash loan. KB: protocols 891 (base), 1690 (ethereum), 893 (optimism); lead 421; bot
`trial-msynth-swap-base`.

## What was measured (Base, 7 days to block 61,039,601, attempts:3934)

- 42 swap transactions by 4 contracts; 38 in one burst of 49 minutes (2026-11-20 15:48:21-16:36:57Z).
- The main incumbent (0x117a6196) takes a fixed 0.57 msETH with 4.3M gas and no fee bidding, and leaves the gap
  open: the farm's executor, as a historical `eth_call`, pays 0.9-2.4 USDC per 400 USDC take from 10 s before the
  first take to the last one. The gap is shallow: 400-800 USDC is the best size, 1,600 USDC already loses.
- Outside a burst the loop loses about 2 pct (state on 2026-11-23).

## How it was found

Not from a protocol list: a Morpho leftover (ynETHx / msETH on ethereum) pointed at msETH trading 13 pct under WETH;
a synth that far from its peg next to a protocol function that still prices it at the oracle is the signal. The
earlier scout rows had read only `liquidate`. Check for the same shape whenever a protocol-issued token is depegged:
is there any protocol function that still converts it at par or at an oracle price?

## Pitfall: the quote depends on block time

On the fork at block 59,998,290 the same `run()` paid 2.833638 USDC in one block and 4.531623 USDC in the next, one
second later, with no state change in between (`eth_call` on `pending` showed the higher value). The protocol's price
read has a time-dependent step (not decoded; likely a staleness fallback between price sources). Two consequences:

1. A fork proof at an old block must pin block time (`anvil_setBlockTimestampInterval 1`, remove it at the end):
   anvil stamps new blocks with the wall clock, days after the forked block, and the guard / success pair then does
   not match the `eth_call`.
2. A live send can pay more or less than the look. The executor's minProfit guard decides; do not assert equality.

## Not done

Ethereum (Pool1 0x3364f53c..., deeper Curve pools, 5 swaps in 7 days) and Optimism; the reverse direction and msBTC;
decoding the time-dependent price step, which could turn the 60 s timer into a known trigger.
