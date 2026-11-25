# Review — 2026-11-11 19:04 UTC

Decision: **fix**. Next review: after the earner changes the manifest, executor payout path, and read cadence. No promotion or fork reproduction was attempted because the current deployment and payout design already fail promotion criteria.

## Blocking findings

1. `allowed_contracts` contains Morpho, Multicall3, USDC, collateral tokens, and pools, although every live send in `bot.js` targets the executor. Set it to `[]`. The signer automatically permits the gate-deployed executor; the current entries authorize direct wallet calls outside that executor and violate `decisions/human/2026-11-11-executor-bots-funds.md`.
2. `MorphoLiquidator.liquidate()` checks that **the executor's** USDC balance rose, then leaves the profit there. `bot.js` has no `sweep` call or other return path. The watchdog and gate count and recover only native gas and USDC in **the bot wallet**. Make each successful action return USDC to the bot wallet in the same transaction, preserving the executor's positive balance guard and atomic flash-loan repayment. Reproduce a profitable success and a guard revert with the changed artifact on the fork.
3. The live read estimate in `manifest.yaml` is **2,500,000 Alchemy CU/day** at 20-second polling, while the manifest estimates only **$1.8/day** of capture profit. Paper heartbeats at 19:02:36–19:03:37 show `rpc_cycle: 5`; that is about 4,320 cycles and 21,600 steady-state RPC calls/day before 5-minute candidate refreshes. This exceeds the approximately 1M CU/day review threshold and is high relative to expected earnings. Widen the polling interval or reduce calls, then measure the revised CU/day and whether the observed opportunity windows remain catchable.

## Other checks

- `tools/manifest-check.py`: PASS. The code reads `EXECUTOR_ADDR` for live deployment. Paper mode does not invoke the signer send branch. Morpho's public liquidation bonus is an intended payout.
- The Solidity source has owner-only `liquidate()`, an atomic Morpho flash loan, and `require(balAfter >= balBefore + minProfit)` after repayment. Live sends use `value: 0`, a signed 460,000 gas limit, and a derived max fee with an in-path USD check against the $20 manifest bound. Fork success/revert evidence in the manifest remains **unverified by this review**.
- Paper ran from 18:09:57 UTC. At 19:03:37 a heartbeat scanned 768 positions, including 381 debtors, with `restamped: 381` and `runtime_ok: true`; no `simulate` row appeared by then. The latest ledger `morpho_blue.liquidate` event observed was block 26392748, before this paper run began. The manifest names pinned-market event block 26391772 as its most recent occurrence.
- This is a fixable design, not a dead payout class: lead 14 remains `measured`; attempt 931 is a `fix_submitted` entry, with no later `dead_end` entry for this bot.

SHA-256 at review: `bot.js` 49e5efea5bb3ebef3165aed27949b9fd15368bbe27efd7d342243c225908f8b1; `manifest.yaml` 9816ba5a7a77a2f97f13c68f3ac3dcd9e796c3ba8f1610ad597d73f752162dd8; `scratch/morpho-executor-eth/contracts/src/MorphoLiquidator.sol` 19c584a18042a3c59065fdce487e1fe7119ed39d7830c3f7297757f993f9a65e. Run ID: 4058f2ea1ef149b0900741c87c71e6cc.
