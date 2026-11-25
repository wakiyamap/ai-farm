---
type: pitfall
chains: [hyperevm, elysium]
protocols: [uniswap_v3]
---

# HyperEVM-style packable ABI: calldata and events use 16-byte words

On chains that run the HyperEVM "packable ABI" (HyperEVM itself; the Elysium Uniswap v3 fork pool
0x97796d80b6a1db78632f7451196b04f307329eb6 with impl 0x1642634c8cb1c9f1b84c9a1a08534f8c3f4e89f8,
measured 2026-11-11 run 5fba44eb), function arguments and event data are packed into 16-byte words
by size (bool 1, uint8 1, int24 3, address 10, uint96/uint160 16 bytes, ...), not standard 32-byte
words. Consequences measured that session:

- An event's non-indexed data starts at the recipient address, not at 32-byte-aligned offsets.
  Parsing a Collect event `Collect(address indexed owner, address recipient, int24 indexed tickLower,
  int24 indexed tickUpper, uint128 amount0, uint128 amount1)` with standard-word slices gave tick
  bounds "231000/233800 that are not tick-spacing multiples" and 40-digit "amounts" - both were the
  packed layout misread. The incumbent position really is ticks 231000..233800 (spacing 100),
  liquidity 1e6.
- Indexed topics stay 32-byte, but a dynamic/indexed mix means `topics[3]` can exist where the event
  ABI does not list it as non-indexed; always take the event signature from the explorer ABI and
  count indexed args before assuming a topic layout.
- `cast calldata --decode` does not exist in foundry 1.9 dist: use `cast decode-calldata "<sig>" <hex>`.
- Explorer ABIs (Etherscan-style `?module=contract&action=getabi`) are the fast pin for these pools
  when the block explorer UI/API is behind a bot challenge: the Kinetiq Elysium explorer returned
  429 on `/api/v2/...` but answered the classic `/api?module=...` endpoint from this host.

Rule: before decoding any calldata/event on these chains, fetch the ABI from the explorer, compute
selectors with `cast keccak`, and decode with `cast decode-calldata`; never slice calldata into
32-byte words by hand.

## Fork CLI notes measured the same run (elysium 9009)

- `fork send` accepts `gas` (not `gasLimit`) in the tx JSON; without a gas field anvil's default
  makes every send fail with "Insufficient funds for gas * price + value".
- `fork fund` (native balance) is wiped by `reset` and by `replay` - re-fund after each of them,
  before the first send.
- `fork deploy <artifact> <from> --args <hex>` does run the constructor (owner() verified); the
  "deploy skips constructors" warning refers to anvil_setCode-style deploys.
- `debug_traceTransaction` works on the 9009 fork (mainnet elysium serves no trace_*), so revert
  frames (incl. the pool's mint callback into the minter) are available only on the fork.
