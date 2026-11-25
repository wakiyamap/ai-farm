---
type: pitfall
chains: [any]
protocols: []
---
# cast abi-encode excludes the function selector

`cast abi-encode "func(types)" values...` prints only the encoded arguments, never the 4-byte selector (the tool help says "excluding the selector"). Appending it to a `cast keccak` prefix is the caller's job: `DATA=$(cast keccak "func(types)" | cut -c1-10)$(cast abi-encode "func(types)" values | sed s/^0x//)`. Two traps seen in one fork-proof session (2026-11-08, run 54b8b740): forgetting the prefix makes every fork call hit the fallback and revert with data `0x` after ~21k gas - the trace shows an empty `calls` list, which looks like a revert inside your own contract; and the args output starts with `0x`, so a naive concatenation produces `0xSELOx000...` ("invalid hex string") - strip the `0x` from the args. Constructor arguments need no selector (that path was correct), only function calls do. Verify with `forge`'s ABI or `cast keccak` before blaming the executor: four identical reverts at 23k gas were calldata, not contract logic.
