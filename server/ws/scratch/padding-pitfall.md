---
type: pitfall
chains: [polygon, any]
protocols: [uncx_network_v3]
---
# `execution reverted` with `data: 0x` and identical gas for every sender = your own calldata is mis-padded

**Conclusion first:** a sub-word integer argument (`uint128`, `uint96`, `uint32`...) must be right-aligned in a full 32-byte word: `"0"*32 + "f"*32` for uint128 max, **not** `"f"*64` (= uint256 max). Pass an over-large word and the ABI decoder reverts before the function body runs: `eth_call` answers `{"code":3,"message":"execution reverted","data":"0x"}` — no revert string, and the **same gas and same empty data whatever `from` you use**, which looks exactly like "everyone is role-reverted". A role revert you did *not* cause carries the string (`"execution reverted: OWNER"`, data `0x08c379a0...`).

**Evidence (polygon, 2026-11-18, UNCX `UNCX_LiquidityLocker_UniV3` 0x40f6301edb774e8B22ADC874f6cb17242BaEB8c4, lock 818, `collect(uint256,address,uint128,uint128)` = 0x260e12b0):** with `"f"*64` maxes the call reverts with empty data at gasUsed 0x5f82 for a stranger, for the recorded lock owner and for the `AUTO_COLLECT_ACCOUNT` alike, and `debug_traceCall {"tracer":"callTracer"}` shows **zero sub-calls** — the revert is before the first external call, so no role was even evaluated. With `"0"*32+"f"*32` (calldata 266 hex = 4 words after the selector, byte-identical in shape to a real collect tx on the same function) the stranger reverts `execution reverted: OWNER` while the lock owner and the AUTO_COLLECT_ACCOUNT both return values. Same contract, same function: the first answer was my encoding, the second was the access control.

**Two cheap checks before writing a revert up as `role_gated`:**

1. Compare your calldata with a real on-chain transaction calling the same function (`eth_getTransactionByHash` → `input`): same length, same word alignment.
2. `debug_traceCall` with the callTracer **does** work on polygon (only `trace_*` is missing there): a reverted root with zero sub-calls whose gasUsed does not move when `from` changes means encoding.

Positive control that the node honours `from`: on the same contract call a function whose only check is the role — `withdraw(818,..)` reverted `OWNER` from a stranger and `NOT YET` from the owner, which is what a real gate looks like.
