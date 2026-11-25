# Review — 2026-11-11 (run fdf829f791c24031919b57c25392b8af)

Decision: **demote**. `next_review_at: null`.

The route has no measured executable capture outside the price-update block in its latest 14-day census. The manifest check passes, but the paper bot does not meet the human's Moonwell relaunch condition or the no-latency-race decision (`decisions/human/2026-11-11-moonwell-stopped.md`, `decisions/human/2026-11-06-no-latency-race.md`). No fork reproduction was needed after the route was ruled out by those decisions.

Evidence:

- Ledger sources `moonwell_core.liquidate_borrow` and `_ext`, blocks 55512916–56090651: 50 captures. Attempts 923–924 correct the earlier whale census. Its two proposed large opportunities, blocks 55648813 and 55717319, were healthy at the preceding block and use watch-only collateral. At 55648812 the correctly decoded liquidity/shortfall was +213.84/0 USD; the bot-exact executor call reverted `NOT_LIQUIDATABLE` (fork tx `0x582cc7069da1b500ad5af22254e29838ea7a57bd43aeca37f6afe11a7cc52ef5`). The previous 1.7 USD/day estimate was withdrawn in attempt 924.
- The one correctly measured capture already eligible before its block, 55572125, borrowed mADA, which `BORROW_MKTS` cannot repay; its estimated gross profit was about 0.6 USD, below the bot's 1 USD send floor (attempt 924). Attempt 923 found zero captures of at least 10 USD repay on enabled collateral routes in the same 14-day window.
- The older WADO success at 53265095 is not an outside-block capture: the current manifest's fork evidence says the eligibility and WADO swap price changed within that capture block. The older 54922711/54922713 window claim cites attempt 644, which used the wrong `getAccountLiquidity` return word; it cannot establish a usable poll window without remeasurement.
- Paper logs from 16:38–17:28Z show advancing heads, `runtime_ok: true`, and detection of a shortfall, but the event was logged `opportunity_watch_only` for mcbETH collateral. No profitable simulation or send appears. The service remains in historical backfill (cursor 54607316 versus head 56138083 at 17:28Z).
- The stated live read estimate is 830,000 Alchemy CU/day at a 180-second cadence, extrapolated from the stopped bot's measured 10M CU/day at 15 seconds. Even taking that estimate at face value, the latest 14-day census supports 0 USD/day from the enabled, catchable route. The active backfill is 40 `eth_getLogs` pages per cycle, so the steady-state estimate does not describe startup consumption.

Reopen only on a new, correctly decoded, executable capture that is liquidatable before its winner's block, has redeemable collateral, clears the bot's send floor after gas, and supports the stated polling cost. The closed same-block class stays `blocked_infra` in lead 18.
