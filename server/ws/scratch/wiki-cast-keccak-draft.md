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
