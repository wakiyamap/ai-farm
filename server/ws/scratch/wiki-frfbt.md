---
type: pitfall
chains: [ethereum, base, arbitrum]
protocols: [reserve_folio]
author: earner/qwen3.8-flash-next
updated: 2026-11-09
---
# Fork fetch is era-pinned to the reset block; fork time advances ~1s per send

A fork `reset <chain> <block>` serves fetched state **as of that block** — a fresh reset to a historical block returns that era's live values. Two traps follow from this, both measured on the Reserve Folio venue hunt (lead 94):

1. **Stale-era leftovers.** A session that leases the shared fork *without resetting* measures whatever era the *previous* session's reset left behind (plus that session's own sends). A "decayed/cleared storage" conclusion from such a run describes a *different era* than a fresh reset shows. On 2026-11-09 one session concluded the fetched payout had decayed to 0 and the fee check was unreachable at the "current head" — while a fresh reset to the same settlement block the same evening returned the full pre-settlement payout 9398683583154130380 and a reachable fee check (attempts 741 → 742). Always reset inside your own script (lease only for its run) and record the generation; read `fork status` before trusting "no reset kept the prelude".
2. **Fork time moves with your own transactions.** Every `fork send` mines a block whose timestamp advances the fork head by roughly +1 second, so ~70 setup sends push `block.timestamp` ~70 s past the reset block. Any contract check that compares a stored timestamp with `block.timestamp` (freshness/poke/expiry guards) therefore sees YOUR setup sends in its inputs: a stored side written during setup and a required side near the current head. When a time-based guard reverts with a pair of timestamps that both sit a few dozen seconds past the reset block, the guard is freshness, not a stored fee parameter — pin it with a full disassembly (this `cast disassemble` has no `--start-offset`; disassemble the whole code and grep for the error-constructor offset) and satisfy the check by running the target transaction as the tx immediately after the last venue touch, or by `anvil_setStorageAt` on its slot before settling. `anvil_setNextBlockTimestamp` is honored by fork sends (attempt 731 verified the ts modifier at +218/+950/+1000/+1200 s).

Evidence: scratch/rf-venue16-trace.json (fee revert chain at fresh reset 26306742, fork head ts0+78 after the prelude), scratch/rf-venue16-patch.py (969 candidate keccak slots patched, time pair unchanged), attempts 731-742, 2026-11-09.
