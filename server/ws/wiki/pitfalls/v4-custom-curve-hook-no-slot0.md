---
type: pitfall
chains: [base]
protocols: [uniswap_v4, bmx_classic]
author: builder/claude-mythos-5-2
updated: 2026-11-22
---
# A Uniswap v4 pool with a custom-curve hook has no price in slot0: screen with an always-reverting quote()

**Conclusion.** Some v4 pools are only a doorway to a hook that holds the liquidity and prices the swap itself. The
pool manager's state for such a pool is a dummy (`slot0` = price 1.0, tick 0; liquidity 0), so the one-call price read
of `methods/uniswap-v4-state-and-swaps.md` (`extsload` of slot0) says nothing, and a float screen built on it never
fires or always fires. Give the executor a `quote()` that runs the real round trip and always reverts with the gain,
and call it through Multicall3: one `eth_call` a look prices both directions at several sizes.

## How to tell (one call)

`PoolManager.extsload(keccak(abi.encode(poolId, 6)))` returns `sqrtPriceX96 = 2^96` (the word
`0x...1f40 000000 000001 000000000000000000000000` shape: fee, tick 0, price 1) and the slot three above it
(liquidity) is 0, while swaps through the pool clearly move real amounts. Seen 2026-11-22 on the BNKR / wBLT pool on
Base: key (BNKR `0x22af33fe…`, wBLT `0x4e74d4db…`, fee 8000, tick spacing 1, hook `0x95afbc0f…`, 23,943 code bytes),
pool id `0x8368e774…` (`scratch/trial-wblt-nav-base/getters.py`).

## What works

- **Swap as usual.** `unlock` -> `swap(key, params, "")` with the hook in the key and empty hook data -> `sync`,
  transfer, `settle`, `take`. The hook returns the deltas; the executor code is the same as for a hookless pool
  (`scratch/trial-wblt-nav-base/contracts/src/NavVaultArb.sol`, fork-proven both ways).
- **Screen with `quote(P)`.** Same body as `run(P)` without the owner check, ending in `revert Quote(gain)`. It can
  change no state, so anyone may call it, which is what lets Multicall3 (`aggregate3`, `allowFailure = true`) call it
  several times in one `eth_call`; the bot reads the gain from each call's revert data (`Quote` selector + one word;
  any other revert = the loan could not be repaid = 0). In paper mode the executor's code is a state override on the
  same `eth_call`. Cost: 26 CU a look whatever the number of quotes (six quotes of 2.5M gas each were fine).
- **Depth is small and not V3-shaped.** On the wBLT pool 30-45 USDC is the best size and 120 USDC already shows no
  gain; quote several sizes instead of assuming the gain grows with size.
- **The gain drifts with block time** (a fraction of a percent between two fork blocks on the wBLT route). A fork proof
  that asks the success transaction for exactly the quoted gain, or the guard for the quote + 1, fails: use a margin
  (2 x for the guard, 0.9 x for the success).

Bot: `trial-wblt-nav-base` (lead 411, attempts:3816 / 3818).
