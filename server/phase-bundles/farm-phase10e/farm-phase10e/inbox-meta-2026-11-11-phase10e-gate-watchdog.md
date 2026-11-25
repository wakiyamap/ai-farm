# Phase 10e (2026-11-11): what changed in the gate, the signer and the watchdog

From the human side. Nothing here needs a decision; please carry the points that concern a role into
its role file / TOOLS.md at your next run (live-operator.md, paper-reviewer.md, earner.md).

1. **`gate promote` now refuses an executor bot whose code never reads its executor address.**
   If the manifest names an `executor:` and no code file of the bot mentions `EXECUTOR_ADDR` or
   `executor.json`, the gate refuses before any funds move ("none of its code reads EXECUTOR_ADDR
   or state/executor.json"). Documentation (.md), manifests and JSON files do not count. This is
   rule 2 of decisions/human/2026-11-11-executor-bots-funds.md, now enforced in code;
   tools/manifest-check.py should make the same check so the earner sees it before review.

2. **`gate stop <id>` can end with "the sweep is incomplete" (exit code 3).**
   The bot's service is stopped, but some funds are not back yet (a chain could not be read, a
   transfer is still pending). The bot then stays in `bots/live/` on purpose: its wallet still
   counts toward X and the watchdog keeps watching it. It is NOT archived and must not be reported
   as stopped-and-swept. Run `gate stop <id>` again later; it resumes where it left off and
   archives once everything is back. `gate sweep <id>` reports the same way. When the watchdog's
   own live-loss stop does not finish, the watchdog repeats it every 10 minutes and says so in its
   inbox/live note.

3. **`gate fund` refuses a top-up that would carry a bot's wallet past 400 USD** (native + USDC now
   in the wallet, plus the top-up). Until now only the promotion checked the per-bot cap.

4. **PnL at stop now includes a gas wallet that was spent down to nothing.** Until now a bot that
   had burned its whole gas float left no PnL record at sweep; it is now booked as a realized loss
   (and counts toward the daily loss limit n).

5. **Signer: `increaseAllowance` follows the `approve` rule** - only to a contract in
   `allowed_contracts` (or the bot's executor), never unlimited.
