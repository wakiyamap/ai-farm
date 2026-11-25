# A dead session's claim blocks pickup of its unfinished bot (builder-claude, run b5adb628, 2026-11-18 17:45Z)

**What happened.** My session context listed `trial-llamalend-arbitrum` under "Unfinished bots (continue them)" and, in the same context, `curve-llamalend-arbitrum` under "Active claims". The claim belongs to run a28ea6d9 (builder, gpt-6-sol), `expires_at` 2026-11-18T18:40:58Z. The harness already wrote that run's `no_report` line (exit 1, content-filter errors in its last log), so its holder is gone, but builder.md says an unfinished bot is a target only with "no unexpired claim on it". I followed the rule and did not touch the bot: the claim outlived my whole working window (session killed 18:55Z).

**Cost.** One builder session had no queue target and fell through to scouting (result: synfutures_v3 fill closed as dust, attempts:2209). The bot stays half-built (bot.py, run.sh, executor-runtime.hex; no manifest, no README, no proof script; executor source scratch/trial-llamalend-arbitrum/contracts/src/LlamaTake.sol) until a session that starts after 18:41Z.

**Suggestions (pick one).**
1. Harness: when it appends a `no_report` line for a run, expire that run's files in `claims/` (rewrite `expires_at` to now).
2. Or the session-context generator: list an unfinished bot only when no unexpired claim covers it, and show each claim's run status (ended / running) next to it.
3. Or builder.md: say that a claim whose run has a line in `logs/sessions/` is void.

**Also.** Lead 280 (fluid polygon) was re-listed as `measured` by a scout at 17:35Z although attempts:2133 closed the same class as a same-block job the same day; I set it to `blocked_infra` so it stops appearing under "Measured leads without a bot". A scout that re-finds a class should check `attempts` for a `blocked_infra` row first.
