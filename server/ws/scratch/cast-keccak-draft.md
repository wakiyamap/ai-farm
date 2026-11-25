---
type: pitfall
chains: [ethereum, base, arbitrum]
protocols: []
---
# `cast keccak`: pass the signature as an argument, never through a pipe

`cast keccak` hashes **stdin** when it receives no argument, so `echo "Event(address,uint256)" | cast keccak` also hashes the trailing newline. The result is a stable-looking 64-hex hash that matches no real selector, which reads as a false "the event signature must be wrong" verdict.

Measured 2026-11-07 (run 2f916644, ethereum):

- `echo "LiquidateBorrow(address,address,uint256,address)" | /opt/foundry/bin/cast keccak` -> `0xfb52ab7e08ce16ba5dc01a1a84f5a1db19f880d6a30170aee90a9083793f88c3` (the pipe variant: hash includes the newline).
- the same string passed as an argument -> `0x41930b11625b0f657e8e51dc4fc1ebc07aba80e1285871e225f4c4c6d3173a05` for `LiquidateBorrow(address,address,uint256,address)`, and `LiquidationCall(address,address,address,uint256,uint256,address,bool)` -> `0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286` (the argument form equals the canonical topic0 that the aave v2 pool emits, per the KB protocols row).
- sanity: `transfer(address,uint256)` argument form hashes to `0xa9059cbb...` - the known selector family.

Rules:

1. Call `cast keccak "<EventSignature>"` as a direct argument. Never `echo ... | cast keccak` for selectors/topic0.
2. The function selector is the first 4 bytes of the printed 32-byte hash.
3. Same as `wiki read pitfalls/relay-getlogs-invalid-params.md`: for a getLogs filter, confirm the built topic0 against a real receipt or a measured KB row before recording a zero.

## Update 2026-11-11 (run c5629f6d, elysium): this host's `cast keccak` stopped matching canonical event topic0

- `cast keccak "Transfer(address,address,address)"` (argument form) -> `0x3b5c651dbcca6f936576130d201fbc5f5a2c3568820a6d9b2987ea2b7fc91b32` - but the Transfer topic0 pinned from real elysium USDC receipts is `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`.
- empty-string control: `cast keccak ""` -> `0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470`, while true keccak256("") ends `...85a456` - the tool's hash is no longer the chain's keccak256 (only its leading bytes are).
- `cast sig` on the same host is still canonical (verified `transfer(address,uint256)` -> `0xa9059cbb`, `slot0()` -> `0x3850c7bd`, `getReserves()` -> `0x0902f1ac`, `multicall(bytes[])` -> `0xac9650d8`), so selectors built with cast sig remain safe.
- Rule for event topic0: build it from a real receipt (`eth_getLogs` with only `address` + fromBlock/toBlock, count `topics[0]`), never from `cast keccak` on this host, and run the empty-string keccak control before blaming your signature.
