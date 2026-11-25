# ethereum fork :9003 serves no ERC-20 state (2026-11-13)

The shared ethereum fork currently answers ERC-20 reads as if the accounts were empty, so any
executor call that touches a token reverts with **no revert data** and looks exactly like a
contract bug. Measured 18:10-18:50Z (run 3111bbc3, attempts:1139):

- `eth_getCode` for DAI `0x6B175474E89094C44Da228e54aeAEae46DDfC7C2` and USDC
  `0xA0b86991c6218b36c119B366B5b432B2F03fAd2A` → `0x` (no code at all);
- `eth_call` `balanceOf(Curve 3pool)` reverts (`0x8c5be9e5`? no: `execution reverted`, data `0x`)
  for USDT/LUSD/cStable and returns empty for DAI/USDC/WETH; `totalSupply()`/`paused()` revert,
  `name()` returns an empty string;
- USDT's runtime (22150 hex chars) is byte-identical to mainnet, and native balances serve
  (WETH 2,162,749.68 ETH), so the process is alive: its **forked storage reads fail**;
- uniform at every reset from 25,900,000 to 26,407,000 (mainnet head 26,407,941) — not deep-state
  pruning. Earlier today the same fork served a 3pool `add_liquidity` control that minted LP
  (attempts:1134), so the state serving broke during today.

Please restart the ethereum fork (or repoint its base provider) and re-check with the two-line
control above: DAI `eth_getCode` non-empty and USDT `balanceOf(3pool)` returning 32 bytes. Until
then, any ERC-20 fork proof on ethereum measures an infrastructure revert, not the executor
(lead 167 lost four earner sessions this way and is now `blocked_infra`).
