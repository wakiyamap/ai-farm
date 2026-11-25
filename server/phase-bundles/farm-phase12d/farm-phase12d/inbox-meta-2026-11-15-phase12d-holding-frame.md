# phase 12d: the holding frame (USDC -> another asset -> USDC, 200 USD in total) (human, 2026-11-15)

## 1. What changed

- **gate-ctl**: `promote` accepts a manifest with `holding_usd` only if: `holding_usd` <= 100 (gate.json `max_holding_usd_per_bot`), `holding_usd` <= `principal_usdc`, an `executor` whose ABI has `exitAll()` with no inputs, `holding_max_hours` with 0 < h <= 168, and `holding_usd` + the `holding_usd` of every live bot <= 200 (`max_holding_usd_total`). Refusals come before anything moves. `stop` calls `exitAll()` on the bot's executor (from the bot key) before the sweep; if that fails, nothing is swept, the bot stays live and the exit code is 3 ("its holdings are NOT back"). `status` has a new `holding_usd` block (per bot, total, limits). New gate.log ops: `exit_sent`, `exit`, `exit_failed`, `exit_skipped`, `exit_gas_topup`.
- **farm-watchdog**: a bot with `holding_usd` is stopped at 30 + `holding_usd` USD of loss since promotion (not 30), and its drop between two balance reads may reach 50 + `holding_usd`. It does not see the price of what the executor holds.
- **Prompts**: common.md (a "Holding frame" paragraph under L; the live-loss stop line), earner.md (section 1 rule, section 3.2, a "Holding frame" bullet in section 5, `holding_usd` in the manifest template), paper-reviewer.md (a "Holding frame" block before "Partial promotion"), live-operator.md (what exit code 3 "its holdings are NOT back" means). The decision file is `decisions/human/2026-11-15-holding-frame.md`: it is already reflected, do not add it again.
- Bots without `holding_usd` are handled exactly as before.

## 2. What I ask of you

1. `tools/manifest-check.py`: accept `holding_usd` and `holding_max_hours`. ERROR when `holding_usd` is not a bare number (the gate parses the line with float(), like `capital_usd`), is above 100, is above `principal_usdc`, when there is no `executor`, when the artifact's ABI has no `exitAll()` with zero inputs, or when `holding_max_hours` is missing, not a bare number, <= 0 or > 168. WARN when `holding_usd` is above 20 and no holding bot has been stopped and swept with real funds yet (the first one should be about 20).
2. A wiki page `methods/holding-frame.md` from the decision file and the earner / reviewer text: the frame, what is in and out (same chain, sellable to USDC in one transaction at any time; no bridge, lock or redemption wait), the executor shape (buy entry with a USDC cap and a minimum received, `exitAll()`, a normal sell entry with a minimum out), the fork proof (buy, `exitAll()` right after, `exitAll()` after `evm_increaseTime` past `holding_max_hours`), what the watchdog does not see, the daily-spend note (USDC sent to the executor counts toward `capital_usd`). Then shorten the earner bullet to point at it: **the assembled earner prompt is now 54,952 bytes, 1,048 under 56,000**.
3. `roles/TOOLS.md`, the gate row: add that `stop` exit 3 can also mean "holdings not back" for a `holding_usd` bot (human decides), and that `status` shows the holding frame.
4. Leads recorded as "holding type" (earner.md section 1 rule since 12a): list them (id, chain, capital, holding time) in your next report, and say which fit the frame (same chain, instant exit, <= 100 USD, <= 7 days). Those are buildable now; the rest stay leads.
5. When the first holding bot is promoted, and when it is first stopped: forward to inbox/human what `gate stop` logged (`exit`, `usdc_back`, the sweep). The stop-and-sweep of a USDC-holding bot has not run with real funds yet.

## 3. Sizes

Assembled after 12d: earner 54,952, paper-reviewer 47,948, researcher 39,380, live-operator 36,443, meta 35,846 bytes.
