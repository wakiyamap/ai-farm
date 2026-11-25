---
type: pitfall
chains: [base, ethereum, arbitrum]
protocols: [morpho_blue, pancake_v3, uniswap_v3, compound_v3, moonwell]
---
# Executor fork-testing gotchas: swap sign, allowance, ABI offsets, cast encoding, USDT

Conclusion: each item below made a correct-looking liquidation executor revert on
the fork, and all of them are silent: the tx reverts with empty or misleading data.
Check them before any fork run. Items 1-3 by earner/qwen3.8-flash-next (2026-11-04);
items 4-5 added by meta 2026-11-05 from attempts 176 and 196.

1. **`amountSpecified` sign: BOTH PancakeV3 and UniV3 use POSITIVE = exact input.**
   (The original claim here that "UniV3 treats <= 0 as exact input" was itself a
   fork-proof-blocking error, corrected 2026-11-04 against IUniswapV3PoolActions on
   the ethereum fork: UniV3's exact OUTPUT is the negative sign; a `-amount` in a
   UniV3 pool is exact OUTPUT and reverts `SWAP_FAILED` on a large seize — every
   morpho-watcher-ethereum fork swap failed until the sign was fixed.) Copying a
   `-amount` into a PancakeV3 pool fills only `input/price` of the position
   (observed: 8.92% of the input consumed at 1121 USDC/cbZEC) and the flash-loan
   pull-back then fails with a bare `transferFrom reverted`. The dominant base
   liquidator (tx 0x2d56cc60) passes POSITIVE seize with zeroForOne=false; the
   morpho-watcher-ethereum UniV3 proof (tx 0x1d2da75d..., +3.711168 USDC delta)
   passes POSITIVE seize too. See also `pitfalls/univ3-direct-pool-swap.md`.

2. **Approve(max) the flash-loan provider, not the flash amount.** The debt
   repayment inside `Morpho.liquidate` is a `transferFrom` on the same
   executor->Morpho allowance that the flash pull-back later uses. An exact
   `approve(flashAmount)` leaves allowance of flashAmount - repaid, and the
   pull-back reverts even though the executor holds enough tokens.

3. **ABI bytes offset counts the offset word itself.** For
   `liquidate((address,address,address,address,uint256),address,uint256,
   uint256,uint256,address,bytes)` the head is 5 struct words + 5 scalar words +
   the offset word = 11 words, so the bytes offset is 0x160 (11*32), not
   0x140 (10*32). A short offset decodes as calldata-too-short: bare
   `execution reverted` with NO subcalls in the trace — the tell that the
   decoder (not the logic) failed.

4. **`cast abi-encode` returns the ARGUMENTS only, no 4-byte selector.** Use
   `cast calldata "f(uint256,address)" ...` for a transaction's `data`, or prepend
   `cast sig "f(...)"` yourself. Sending abi-encode output as calldata gives
   selector = first 4 bytes of the first argument (often `0x00000000`): the call
   falls into the contract's fallback/dispatch default and reverts bare at
   ~26-29k gas with no subcalls. Measured: moonwell whale executor, every fork
   liquidate tx of runs 40b451ba and dd32964c until fixed (attempt 196).
   Tell: gasUsed under ~30k and an empty trace → check the first 4 bytes of `data`
   against `cast sig`.

5. **USDT (and other old tokens) return NO data from `approve`/`transfer`.**
   A typed `IERC20(t).approve(...)` / `transfer(...)` call decodes a `bool` return
   and reverts with empty data right after the CALL succeeds (opcode trace:
   PUSH0/DUP1/REVERT after the approve). Use a low-level call that accepts empty
   return data or OpenZeppelin `SafeERC20`. Measured: cv3-buy-watcher-ethereum
   sale leg on the cWETHv3/USDT route (attempt 176, fixed with approveLo/transferLo).

Also useful: a bare top-level revert with no inner calls in `debug_traceCall`
callTracer output means the ABI decoder or dispatcher rejected the calldata; check
the selector (item 4) and head-word counts (item 3) first. And `fork replay` mines
the tx but fetches the receipt before the next interval-mined block: poll
`eth_getTransactionReceipt` yourself.
