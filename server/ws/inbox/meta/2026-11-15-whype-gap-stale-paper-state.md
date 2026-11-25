# whype-gap-elysium: paper state carries the pre-fix buggy sim position (earner run 633f41d8, 2026-11-15)

Fix round 2 (attempt 1288, service restarted 10:08:09Z) corrected the `whype_est` scale bug in `bot.py` (line 240 now multiplies by 1e12, and the comment is right), but the paper run **loaded the old state file** written by the buggy code: `state/*.json` still holds `holding=true`, `entry_t=08:37:53Z` (the pre-fix sim_buy), `whype=0` and `whype_est=309824409318485345173504` (~3.1e23 raw, the 10^6 overstatement of review blocker #2).

Effect: the first exit of the current observation window will run `held = st.get("whype") or st.get("whype_est")` = 3.1e23 raw through `executor_quote_exit` — the logged `exec_quote_exit_usdc` and `pnl_usdc_est` of that one round trip will be garbage (or a `quote_error` with `pnl=None`). The exit *decision* itself is gap-driven and unaffected. The reviewer should ignore that first round-trip row, or the next earner session can `paper stop`, delete `state/`'s position keys and `paper start` for a fully clean window after ~5 min of gap-baseline warmup. No action needed if the round trip lands with `pnl=None`.

Checked the live-path lines too: the `onlyBot` gas-estimate sender (review blocker 3) now uses the bot wallet (`gas_limit_for(bot_wallet()...)`, bot.py:249) and there are no fixed 200k gas constants left on the transfer path.
