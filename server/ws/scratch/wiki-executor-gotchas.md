---
type: pitfall
chains: [base]
protocols: [morpho_blue, pancake_v3]
---
# Executor fork-testing gotchas: PancakeV3 swap sign, allowance, and ABI offsets

Conclusion: three separate one-line bugs each made a correct-looking Morpho
liquidation executor revert on the fork. All three are silent: the tx reverts
with empty or misleading data. Check them before any fork run.

1. **PancakeV3 `amountSpecified` sign is inverted vs UniV3.** PancakeV3Pool.swap
   treats `amountSpecified > 0` as exact INPUT; UniV3 treats `<= 0` as exact
   input. Copying a UniV3-style `-amount` into a PancakeV3 pool fills only
   `input/price` of the position (observed: 8.92% of the input consumed at
   1121 USDC/cbZEC) and the flash-loan pull-back then fails with a bare
   `transferFrom reverted`. The dominant base liquidator (tx 0x2d56cc60) passes
   POSITIVE seize with zeroForOne=false.

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

Also useful: a bare top-level revert with no inner calls in `debug_traceCall`
callTracer output means the ABI decoder rejected the calldata; check head-word
counts first. And `fork replay` mines the tx but fetches the receipt before the
next interval-mined block: poll `eth_getTransactionReceipt` yourself.
