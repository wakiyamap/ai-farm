---
type: pitfall
chains: [ethereum]
protocols: [compound_v3, uniswap_v3]
---

# Verify every selector on-chain before encoding (ethereum relay)

## Conclusion first
Guessing function selectors from memory cost this session four failed probe
rounds on ethereum. Compute keccak-256 selectors (host `Cryptodome.Hash.keccak`,
digest_bits=256 — plain SHA3 is a different padding) and verify each call once
with a real `eth_call` through the relay before trusting it. A wrong selector on
a contract with no fallback comes back `execution reverted` (code 3), NOT "unknown
function" — that is the signal the selector is wrong, not the network.

## What was wrong
- `getPool(address,address,uint24)` is `0x1698ee82`, not the 0x5d861afe many
  integrations remember; the guessed value reverted on the Uniswap v3 factory.
- `slot0()` is `0x3850c7bd`, not 0x385a51f9 (the latter also reverted).
- `factory()` is `0xc45a0155`; on a v3 pool `factory()`/`slot0()` with the
  correct selectors succeed, so they are a cheap pool-identity check.
- Comet ABI from the executor bytecode is authoritative when the contract is
  fork-proven: `getCollateralReserves(address)` `0x9ff567f8`,
  `quoteCollateral(address,uint256)` `0x7ac88ed1`,
  `buyCollateral(address,uint256,uint256,address)` `0xe4e6e779`,
  `baseToken()` `0xc55dae63`. Note `0xd21220a7` is pool `token1()`, not
  quoteCollateral — two selectors in the same bot's call list looked similar.

## The factory address trap
`0x1f9840a85b5aee85c1f47e4b4784dd98ee35e2e6` (the pattern the UNI token shares)
has NO code on mainnet — `eth_getCode` length 2 is the fail-closed signal, and
calls to it return empty `0x` rather than reverting. The real Uniswap v3 factory
is `0x1f98431c8ad98523631ae4a59f267346ea31f984`: read it from the factory's
`Deploy` event in the pool's deploy transaction receipt (the receipt is only
served on the `live` relay lane — `research`/`paper` returned null here).

## Relay quirks measured 2026-11-04
- `eth_call` accepts a third `stateOverride` parameter (`{address:{code}}`) —
  the paper-executor sim depends on it.
- An `eth_call` of a pool `swap(...)` with `zeroForOne=true` + positive
  `amountSpecified` from an empty-code sender REVERTS (exact-input pays the
  input via transferFrom of the caller); the exact-output direction
  (negative amountSpecified) simulates fine from an empty account.
- Wide `eth_getLogs` windows are rejected ("all providers failed: alchemy:
  HTTP 400"); page them like `tools/relay-log-scan.py` does.

Evidence: probes scratch/cv3-pools2.js (pools for WETH/WBTC/LINK/UNI vs USDC),
scratch/cv3-factory4.js (factory via deploy receipt, block 12376729, tx
receipt of pool 0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640), attempts rows 63,
76, 89.
