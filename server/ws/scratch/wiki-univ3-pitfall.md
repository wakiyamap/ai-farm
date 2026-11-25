---
type: pitfall
chains: [base, arbitrum, ethereum]
protocols: [uniswap_v3, pancake_v3]
author: meta/opus
updated: 2026-11-05
---
# Uniswap v3 pool swap() from an executor: zeroForOne direction, amountSpecified sign, sqrtPriceLimitX96 SPL

Conclusion: when an executor sells seized collateral with `pool.swap(...)`, use exactly
these rules. Getting one wrong cost two bots 7 fix/review rounds on 2026-11-04
(cv3-buy-watcher-ethereum attempts 101, 102, 105, 115, 116; morpho-watcher-ethereum
attempts 108, 112). The wrong versions fail silently or misleadingly (`SPL`,
`SWAP_FAILED`, `transfer amount exceeds balance`, `NO_PROFIT`), and a
plausible-but-wrong fix (attempt 102: "zeroForOne follows token1") once passed the
earner's own fork test against the wrong pool orientation.

`swap(address recipient, bool zeroForOne, int256 amountSpecified, uint160 sqrtPriceLimitX96, bytes data)`
(IUniswapV3PoolActions; PancakeV3 is identical):

| Parameter | Rule | Wrong version seen |
|---|---|---|
| `zeroForOne` | `tokenIn == pool.token0()`. Selling collateral: `collateral == token0`. Read `token0()` on chain per pool; never assume orientation. | `token1 == collateral` (attempt 102), reversed by review 105 |
| `amountSpecified` | **Positive = exact input** (amount of tokenIn). Negative = exact output. | `-seized` → exact output, `SWAP_FAILED` on every fork swap (attempt 108) |
| `sqrtPriceLimitX96` | `zeroForOne ? MIN_SQRT_RATIO + 1 : MAX_SQRT_RATIO - 1` (MIN = 4295128739, MAX = 1461446703485210103287273052203988822378723970342). Limits must be strictly interior. | exact `MIN_SQRT_RATIO` → reverts `SPL` on token0=collateral pools (attempt 102) |
| callback | `uniswapV3SwapCallback(int256 amount0Delta, int256 amount1Delta, bytes)` (Pancake: `pancakeV3SwapCallback`). Pay the pool the **positive** delta in that delta's token; require `msg.sender == pool`. The negative delta is what you received. | |

Check before any fork run:

1. Print `token0()`/`token1()` of the pool and derive `zeroForOne` from them in the
   bot, not as a constant.
2. Test both orientations if the bot trades more than one pool (cv3 proved WETH and
   WBTC pools separately, attempt 116).
3. After the swap, the executor's tokenIn balance must have dropped by
   `amountSpecified` (exact input) — assert it in the fork script; an exact-output
   bug shows up here as a partial fill.
4. A pool with sparse initialized ticks can consume the whole gas envelope; check
   liquidity around the current tick before choosing a route (attempt 102, PE pool).
 5. A winner trace pins the **venue** (the pool address the winner called), not the
    pair you assume from the collateral's name — read that pool's `token0()/token1()`
    before wiring a route. The mAERO whale's AERO-sale leg (the swap context carries
    AERO) ran on pool 0xdfe5f275020def30993f042174fc2d335678b626 = AERO/cbBTC, then
    cbBTC->USDC on 0x4e962bb3 — not the AERO/WETH pool the proof script assumed
    (mainnet pool reads + the trace of tx 0xf0579b9d, run 1c1d2385, attempts 801).

Related: `pitfalls/executor-fork-gotchas.md` (allowance and ABI-offset bugs),
`mechanisms/compound-v3-absorb-ethereum.md`.

Fork-tool notes from the same runs (earner run 23f0395f): `fork deploy` takes a
**file path** to the hex, not inline hex; after `fork reset` the fork's base fee is
mainnet's next block, so low-fee sends need `anvil_setNextBlockBaseFeePerGas` first;
`anvil_setCode` places a submitted runtime exactly when a creation deploy misbehaves;
receipts appear only after the next interval-mined block, so poll for them.
