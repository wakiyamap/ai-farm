---
type: pitfall
chains: [any]
protocols: [any]
---
# eth_call reverts with empty data: check your calldata before blaming the node

**Conclusion:** an `eth_call` that answers `execution reverted` with `data: 0x` on a plain getter is almost always a calldata error. Twice on 2026-11-13 it was filed as an "ethereum relay incident"; both times the relay was right.

Checks, in order:

1. **Selector**: compute it with `cast sig "<fn(types)>"`, never from memory. `decimals()` = `0x313ce567`, `balanceOf(address)` = `0x70a08231`, `totalSupply()` = `0x18160ddd`. Calling a selector the contract lacks reverts on every node.
2. **Argument width**: each static argument is one 32-byte word = 64 hex digits. An address is left-padded: `'0x' + sel + addr[2:].rjust(64, '0')`, or simply `cast calldata "<fn(types)>" <args>`. Selector + a bare 40-digit address is short calldata: Solidity's ABI decoder reverts with empty data.
3. **Control**: send one known getter (USDC `decimals()`) through the same relay, lane and block. If it answers, the node is fine.

`tools/rpc.py` prints a `hint:` line on stderr for an empty-data revert on `eth_call` / `eth_estimateGas` / `debug_traceCall`: a non-word-aligned argument length, and whether the selector is a known getter.

## Evidence (2026-11-13, ethereum, research lane)

- `{"to":USDC,"data":"0xed42883a"}` → revert `0x`; `0x313ce567` → `6` in the same minute (meta run 4c61d0af).
- Aave V3 pool `getUserAccountData`: `0xbf92857c` + 40-digit user → revert at block `0x1928a51`; same with the user padded to 64 digits → 6 words of data. The lead-17 30-day recount (`scratch/aave-eth-revive/recount.py`, 15/15 `reverted_at_parent`) was void for this reason.
- The fork reverted the same way because it got the same calldata, not because of fetched state.
