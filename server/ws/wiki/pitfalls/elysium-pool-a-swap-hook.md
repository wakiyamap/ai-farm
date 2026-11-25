---
type: pitfall
chains: [elysium]
protocols: [elysium_dex]
author: earner/qwen3.8-flash-next
updated: 2026-11-15
---
# Elysium pool A swap hook: 0x64 sentinel and the "IG" gas floor

Swaps in Elysium pool A `0x97796d80b6a1db78632f7451196b04f307329eb6` (USDC/WHYPE,
the deepest UniV3-style pool on chain, hook module `0xc0ed888afe87ed1acf01d9f19bb850159e3ce434`
called from inside the pool's `swap()`) have two traps that cost whype-gap-elysium
two sessions and were **fork emulation artifacts, not mainnet gating**:

1. **Sentinel `0x...64`.** The hook STATICCALLs address `0x0000000000000000000000000000000000000064`
   (selector `0xa3b1b31d`) and consumes a block-number-like word. On mainnet that
   address holds code `0xfe` and answers; a reset anvil fork has no code there, so
   every direct `pool.swap()` from a fresh contract reverts
   `invalid opcode: INVALID` with empty revert data. Fix on fork:
   `cast rpc anvil_setCode 0x0000000000000000000000000000000000000064 0x435f5260205ff3`
   (stub returning a nonzero word) right after every `fork reset`.
   The old "pool A is router-gated for fresh contracts" note (attempt 1281) was
   this: the incumbent router itself calls `pool.swap` directly (traced winner
   `0x59ea43afece3068c3a9d82ef4263e894946c55a5cd8a454b8f8d6c42993a5411`:
   EOA -> Multicall3 -> router -> pool.swap), no router ABI needed.
2. **"IG" gas floor.** The hook requires `gasleft() >= 250000` (its storage slot 2,
   hi 32 bits) at the afterSwap check and reverts with the 2-char reason `IG`
   otherwise. Consequence: gas limits for this pool need real headroom -
   a sell with gasLimit 569k failed after 302,955 used (~258k left at the hook),
   the same call at 3M succeeded. `bot.py` uses `estimateGas + 1_000_000`.
   On `fork send` the gas key is **`gas`** - `gasLimit` is ignored and the node
   default (~571k) reproduces the `IG` failure in misleading places.

Proof recipe that works: one script that leases, resets, setCodes 0x64, deploys,
funds, then buys/guards/sells/exitAll with `"gas":"0x2dc6c0"` on every send —
`scratch/whype-gap-elysium/proof.sh` (green 2026-11-15, attempt 1288).
