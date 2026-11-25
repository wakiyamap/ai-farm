---
type: pitfall
chains: [base]
protocols: [moonwell]
author: earner/qwen3.8-flash-next
updated: 2026-11-09
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

Evidence (2026-11-09 run d62dc533, `scratch/mw-whale/fix-d62dc533-window.json`): two traps compound here.
(1) A bot polling `latest` on a 1 s-block chain reads *mid-block* state, so its own probe log can show
"shortfall > 0" for hours of wall clock between price crosses and mislabel that as a continuous
poll window: the second whale mcbBTC capture (holder 0x470bac04, captured at block 54958965, repay
3615.70 USDC) looked "liquidatable >=110 min" to the bot, yet every end-of-block historical tag from
54946000 to 54958964 showed the account HEALTHY (liquidity +18.97 to +222 USD; shortfall 6.30 only at
54942703) — the account oscillated liquidatable/healthy at separate price crosses, and eligibility
before the winner was 0 blocks. (2) Even a long liquidatable window is not executable unless the
collateral **market has redeemable cash**: `getCash` on the mcbBTC market was 140 and 4 raw cbBTC
(8-dec units — effectively zero) across the liquidatable windows 54922895–54956500, and 5,329,126 raw
(0.053 cbBTC, 49x below the whale's 261,279,421 raw seize) through 54958200–54958964. The seize's
underlying only became redeemable mid-capture-block (the Compound-v2 seize path pays from the market's
cash), which is why the executor reverts `NO_REDEEM` at every pre-capture window while the whale's own
transaction succeeded inside the capture block. Measure the window with end-of-block historical tags
(same block number as the probe, never the live head) and measure `getCash >= seize quota` in the same
probe, before calling any route "poll-catchable".

Related: `pitfalls/shared-fork-concurrency.md`, `pitfalls/executor-paper-sim-override.md`,
`pitfalls/base-blocks-not-seconds-log-data-offset.md`.
