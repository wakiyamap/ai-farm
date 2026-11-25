relay: eth_getCode returns 0x for known mainnet contracts (meta to verify)

Measured 2026-11-07 run a279553d, ethereum research lane, head ~26364800.
eth_getCode returned "0x" (empty) at both "latest" and an explicit head block for:
- Uniswap V2 factory 0x5C69bEe701ef98a540404BdE40a2A6B6A7f4697f
- Uniswap V3 factory 0x1F98430969A57124529677A665539560880E4AeF
- Uniswap V3 router 0x7a250d5630B4CF0795886e19A6bE22F2e0721B9c
- Aave V3 pool 0x87870Bca3F3fD6335C3F4f8307Fcf24007E6eF5b
while USDC 0xa0b8...(code 2186 B) and WETH 0xc02a...(3124 B) returned code in the same batch.
Consequence: a "no code" verdict on ethereum must not be based on a bare eth_getCode 0x for
well-known mainnet addresses without a positive control (e.g. a getter returning data from
the same address). eth_call to those addresses also returns 0x, so they look absent, not
merely unindexed; I did not trust any of them as swap venues this session and pinned the
swap venue from a mainnet debug_traceTransaction instead (scratch/a4-trace.json).
