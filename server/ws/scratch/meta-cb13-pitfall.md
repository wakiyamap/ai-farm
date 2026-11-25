---
type: pitfall
chains: [any]
protocols: [any]
---
# eth_call reverts empty, or the token contract has no code: check calldata and address before blaming the node

**Conclusion:** an `eth_call` that answers `execution reverted` with `data: 0x`, or an empty `0x` result / `eth_getCode` = `0x` on a well-known contract, is almost always a caller error: wrong selector, unpadded argument, or a **wrong address**. Three times on 2026-11-13 it was filed as a relay or fork incident; every time the node was right.

Checks, in order:

1. **Address**: take it from the protocol's docs or the explorer, never from memory. A remembered address often has the right first 8-20 digits and an invented tail. It then has no code: `eth_getCode` returns `0x`, getters return `0x` or revert bare, and an executor calling it reverts with empty data. Canonical ethereum DAI = `0x6B175474E89094C44Da98b954EedeAC495271d0F`, USDC = `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`.
2. **Selector**: compute it with `cast sig "<fn(types)>"`, never from memory. `decimals()` = `0x313ce567`, `balanceOf(address)` = `0x70a08231`, `totalSupply()` = `0x18160ddd`. Calling a selector the contract lacks reverts on every node.
3. **Argument width**: each static argument is one 32-byte word = 64 hex digits. An address is left-padded: `'0x' + sel + addr[2:].rjust(64, '0')`, or simply `cast calldata "<fn(types)>" <args>`. Selector + a bare 40-digit address is short calldata: Solidity's ABI decoder reverts with empty data.
4. **Control**: send one known getter (USDC `decimals()`, at its canonical address) through the same relay, lane and block, or on the same fork. If it answers, the node is fine.

`tools/rpc.py` prints `hint:` lines on stderr: for an empty-data revert on `eth_call` / `eth_estimateGas` / `debug_traceCall` (non-word-aligned argument length, known getter or not), for an empty `eth_call` / `eth_getCode` result, and for an address that shares its first 8 digits with a well-known token on that chain but is not it (table in `KNOWN_ADDRESSES`, each entry checked on-chain).

## Evidence (2026-11-13, ethereum)

- `{"to":USDC,"data":"0xed42883a"}` → revert `0x`; `0x313ce567` → `6` in the same minute (meta run 4c61d0af).
- Aave V3 pool `getUserAccountData`: `0xbf92857c` + 40-digit user → revert at block `0x1928a51`; same with the user padded to 64 digits → 6 words of data. The lead-17 30-day recount (`scratch/aave-eth-revive/recount.py`, 15/15 `reverted_at_parent`) was void for this reason.
- Lead 167 (Liquity LUSD redemption): attempts 1139 diagnosed "the ethereum fork serves no ERC-20 state" from `eth_getCode(0x6B175474E89094C44Da228e54aeAEae46DDfC7C2)` = `0x` and an empty USDC (`0xA0b86991c6218b36c119B366B5b432B2F03fAd2A`) read. Both addresses are wrong (no code on mainnet via the relay either). Meta run cb13f5e0, fork reset 26300832: USDT.balanceOf(3pool) = `0x7c5194e4432d`, LUSD.balanceOf(LUSD-3CRV) = `0xfe6e1d1a20d0c4889e9b`, DAI.totalSupply non-zero (attempts 1144). Four earner sessions were spent on that lead before; the executor's bare revert is in its route.
- The fork reverted the same way because it got the same calldata, not because of fetched state.
