# fork 9003 ethereum: USDT/LUSD/cStable state reverts at head 26300845 (run 4b0c8c2a)

2026-11-13 ~20:40-21:00Z. Shared ethereum fork (lease held, gen 680, released by this session).

Symptom (after `fork reset`, also at current head): `eth_call` to USDT `0xdac17F958D2ee523a2206206994597C13D831eC7`,
LUSD, cStable, 3pool for `balanceOf(anyone)` / `paused()` / `slot0 getter` reverts bare
(`execution reverted`, data `0x`) while `eth_getCode` returns full bytecode and pure/deep-fetchable reads work:
USDT `decimals()` returns 6, `totalSupply()` returns 0x139b58888d05866, PriceFeed `fetchPrice`,
HintHelpers `getRedemptionHints`, SortedTroves `getSize` all fine.
`fork fund-token ... $ rc=0` (storage write, not serving proof). An executor redeem dies inside
Morpho flashLoan's `USDT.transfer` with `invalid opcode: INVALID` (callTracer), i.e. state reads for these
tokens fail mid-call too. `eth_getStorageAt` on the relay answers fine; not relay quota
(research 262k/1M CU at 21:2xZ). Retried 3 full proof runs + delayed retry: unchanged.

Same signature recorded by attempts:1139 (blocked_infra) on an earlier instance; attempts:1145's proof6
passed USDT balanceOf reads on this reset earlier today, so serving broke after the ~18:5xZ fork restart.
Please check the fork instance's base-RPC state provider (deep-slot fetch failures present as bare
`execution reverted`) and restart :9003 when convenient; re-check with:
`eth_call [{"to":"0xdac17F958D2ee523a2206206994597C13D831eC7","data":"0x70a08201000000000000000000000000bEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"}]`
→ must return 32 bytes.
