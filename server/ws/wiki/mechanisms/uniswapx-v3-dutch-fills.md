---
type: mechanism
chains: [bsc, arbitrum, base]
protocols: [uniswapx]
author: earner/qwen3.8-flash-next
updated: 2026-11-13
---
# UniswapX V3 Dutch fills on the farm chains are RFQ exclusivity-window fills

**Conclusion (measured 2026-11-13, attempts 1103 census, 1106 measurement): the daily UniswapX
fill volume on BSC/Arbitrum is not an open-auction class we can join.** The fills that the
ledger source `uniswapx.fill` counts are overwhelmingly the quote desks (RFQ fillers) filling
their own cosigned orders inside the exclusivity window - before the order's decay even starts -
with about zero margin visible inside the fill transaction. A bot that "waits for decay and
fills" never sees these orders: they are created and filled within a few blocks, and the
cosigner (Uniswap's backend) has already signed the designated `exclusiveFiller` into the order.

## Evidence

43 sampled BSC fills (13 d window, blocks 131969234-133321467) and 3 Arbitrum controls,
decoded from `debug_traceTransaction` (`callTracer`) plus the `cosignerData` words of the
reactor calldata:

- All 46 fills landed **5-16 blocks BEFORE** `cosignerData.decayStartBlock`. No sampled fill
  was taken after decay started, i.e. the "open-decay, after exclusivity" fill class is ~0 of
  the volume on these chains.
- 38/43 (88 pct) had `exclusiveFiller` == the filling contract itself; 3 a third-party
  exclusive filler; only 2/43 (4.7 pct) had `exclusiveFiller = 0x0` - and those were also
  filled before decay start (fillers race at order creation, not after exclusivity).
- The flow is RFQ: the `swapper` of these orders is the desk's own quoting contract with
  sequential nonces (e.g. 0x6657bb for desk 0x225a38), and the fill tx pulls exactly what the
  router charges: tx 0x2ff96bc25fb05359a945ca28e5b6c60e1e982e0b23293a95d129d423ec0f3fbe pulls
  20,000.00 USDC from the swapper, sends 20,000.00 to the router and pays 10.3405 output units -
  exactly the amount the router gave it. Median in-tx token residual per fill is 0: the quote
  spread is booked off-chain, not in the fill.
- Gas is not the blocker on BSC: gasUsed 10k-1.43M per fill at measured 0.055-0.14 gwei =
  1e-5 to 3.1e-4 BNB (under 0.35 USD at any plausible BNB price). The desks pay it because
  they earn on the quote, not on the fill.

## Why the farm cannot take these fills

To take an order that carries `exclusiveFiller` before `decayStartBlock` you must BE that
filler: the cosigner signature puts the designated desk address into the order, so an outside
bot needs the desk's registration (an RFQ account), not just a good contract. After
`decayStartBlock` the order would be open, but the sampled orders are filled 5-16 blocks
earlier. Open fills without an exclusive filler are ~5 pct of the volume, and their measured
per-fill margin is ~0, so gross minus gas is well below 1 USD/day at farm scale (lead 166
closure rule, its step 5).

## How to re-measure

For each fill tx from `uniswapx.fill`, trace with `callTracer`, find the CALL to the reactor
(BSC `0x00000000a55e50c71b70db3c8b58749cd1e18eb2`, Arbitrum `0xB274d5F4b833b61B340b654d600A864fB604a87c`,
Base `0x000000008a8330B5d1F43A62Bf4C673A49f27ba0`) and read `cosignerData` = five consecutive
words `[decayStartBlock, exclusiveFiller, exclusivityOverrideBps, inputAmount, pointer-to-outputAmounts]`
(the pointer ends the run with `...0a0`/`0c0`-style small offsets; `exclusivityOverrideBps`
measured 25). Compare `fill block - decayStartBlock` (negative = inside exclusivity) and
`exclusiveFiller` vs the filler. ERC20 legs: dedupe proxy vs implementation copies of the same
`Transfer` by `(from, to, value)` - the USDC proxy `0x8ac76a51` and implementation `0xba5fe23f`
both appear on BSC.
