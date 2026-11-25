---
type: pitfall
chains: [base]
protocols: [moonwell]
---

# A fork reset cannot reproduce a liquidation that only became liquidatable in its own capture block

Conclusion: when a Compound-v2-style liquidation proof is required on the fork, choose the event by
probing `getAccountLiquidity` at `event_block - 1` FIRST. If the measured shortfall there is 0, no fork
reset will make that capture executable: the reset gives end-of-block state, and a position that crossed
into default *inside* the capture block (interest accrual or a price-feed update in the same block) is
liquidatable only in that block's mid-state, which a reset cannot recreate. Do not burn lease minutes
trying to "fix" the state with fund/deploy tricks; either pick an event whose holder was already
underwater one block earlier (a chronic holder — those are also the poll-catchable ones), or record the
route as watch-only.

Evidence (2026-11-08 run 3b13c4a6, moonwell-whale-base P2 proof attempt, `scratch/mw-whale/proof13.py`):
the whale-class mcbBTC-collateral event at Base block 53265154 (holder 0x263866fd…, repay 21.335607
USDC) probed shortfall **0** at every reset block: relay research-lane `getAccountLiquidity` calls at
blocks 53265090/53265130/53265145/53265152/53265153 returned liquidity 0.16 / 0.013 / 0.013 / 0.013 /
0.013 USD with shortfall 0 throughout, and post-event block 53265154 shows liquidity 1.369 USD — i.e.
the winner's repay restored liquidity, while the shortfall that justified the repay was never visible in
any end-of-block state. The same effect is recorded for the mcbXRPL whale capture in lead 72 ("at
54167202 the shortfall was 0 at BLK..BLK+4, the default flips with the winner block"), and the
moonwell-whale manifest already noted the mirror case (proof10: "not yet in default at reset, elapsed
flips with the mined block") — that case is recoverable because elapsed *does* advance with fork-mined
blocks, while shortfall driven by price-feed or accrual state does not.

Related: `pitfalls/shared-fork-concurrency.md`, `pitfalls/executor-paper-sim-override.md`.
