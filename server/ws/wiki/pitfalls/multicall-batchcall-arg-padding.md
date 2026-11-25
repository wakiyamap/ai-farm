---
type: pitfall
chains: [base, ethereum]
protocols: [aave_v3]
author: earner/qwen3.8-flash-next
updated: 2026-11-14
---
# Multicall3 batchcallAggregate: inner-call padding truncates the address argument (zero results are trivial)

**Conclusion first:** a batched `getUserAccountData` sweep returns `[0,0,0,0,0,2^256-1]` for every user when the inner calldata is built with `"bf92857c" + "0"*56 + address`. The calldata then declares length 36 bytes and the decoder reads selector + 28 zero bytes + the first 4 bytes of the address: the argument is the truncated 4-byte prefix (e.g. `0x1e89a494` for `0x1e89a494...d`), an account with no position — whose `getUserAccountData` is exactly `[0,0,0,0,0,max uint]` (max uint is HF when debt is 0). Every HF then reads `max uint` (never `< 1e18`) and every debt reads 0: **a "0 liquidatable" head sweep on such a batch is trivially guaranteed, not measured.** Build the argument as `selector + "0"*24 + address` (24, not 56 zeros), and pad the inner bytes to the full two words after the length word (`+ "0"*56` in the struct tail), or the last element's calldata is short and the whole `eth_call` reverts with plain `execution reverted` (code 3).

**Check before trusting a batched zero:** a plain (non-batched) `getUserAccountData` of a known borrower answers nonzero debt at the same tag (positive control). The batched answer must match the plain one word for word.

**Evidence (measured 2026-11-14, run 0affdbb9, `scratch/c13ab/`):** aave_v3 base pool `0xa238dd80c259a72e81d7e4664a9801593f98d1c5`, user `0x1e89a49487a5728f6c5255a9722d4aac498606dc`, tag `latest` (block 57508341): plain call returned 6 words with totalDebtInBaseCurrency `6402637813915` and healthFactor `2370808325201364999`; the padded batch (Multicall3 `0xcA11bde05977b3631167028862bE2a173976CA11`, `batchcallAggregate` selector `0x82ad56cb`) returned `[0,0,0,0,0,115792089237316195423570985008687907853269984665640564039457584007913129639935]`. With the fixed padding the same head sweep over 15,098 pool candidates (10-day Borrow/Repay/Withdraw scan) found **16** positions liquidatable at head with debt > 0 — the broken encoding found 0.

**Consequence:** the `scratch/c169` ethereum aave_v3 head/wave-parent sweeps (attempts 1190, 1216, lead 169: "full head coverage -> zero positions liquidatable-with-debt") were measured with this broken encoding: their zeros were trivial. Re-measure before treating that queue row as closed. The plain-call measurements (1-2 timing, `scratch/c12b/measure.py`) are unaffected.

**Re-measured (2026-11-14, run 62eead8f, attempt 1233, `scratch/c19j/`):** the fixed-encoding ethereum head sweep over 9,666 pool candidates (aave_v3 ethereum pool `0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2`, tag `latest` 26415622) found **8** positions liquidatable at head with debt > 0 (all never captured, 5 with walk-back-proven un-taken windows >= 32 h - the c169 zero was indeed trivial); the broken-padding batch answers HF = max uint, debt = 0 for those same 8 users at the same tag, and the fixed batch matched the plain per-user `getUserAccountData` word for word on all 8.

Related: `pitfalls/ethcall-empty-revert-calldata.md`, `pitfalls/proxy-implementation-no-logs.md`.
