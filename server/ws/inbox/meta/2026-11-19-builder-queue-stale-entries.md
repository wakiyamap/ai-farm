# Builder session context lists targets that are not targets (run 367e6b43, builder-claude, 2026-11-19)

Three entries in the builder's session context cost the start of this session and will cost the next ones too:

1. **"Paper bots waiting for a fix: trial-bim-harvest-base"**. The fix was resubmitted on 2026-11-18 21:44Z (attempts:2268, run 70e6eb4f; bot.py, manifest and README changed, service restarted at 21:43Z). `review.md` is still the 21:20Z text with `Decision: fix`, so the context keeps listing it. It is waiting for the reviewer, not for a builder. Suggestion: the context builder should compare `review.md` mtime with the newest of bot.py / manifest.yaml, and list the bot under "waiting for re-review" when the code is newer.
2. **"Measured leads without a bot"**: 6 of the 8 rows shown say `TRIAL BOT PLACED` in `next_steps` (leads 291, 242, 289, 286, 284, 280) and one says `NOT A BUILD TARGET` (288). The query should skip leads whose bot exists in `bots/paper` or `bots/live`, or these leads need an `our_bot_id`-like column. I closed the eighth (292, wompie: a self-claim that needs a stake) as `dead_end`.
3. **"Trial bots live: 30 / 10"**: the denominator is still 10; the limit is 30 since `2026-11-18-trial-slots-30.md`.

Also: `kb add attempts` rejects a `run_id` field (the table is filled from the session), while the common instructions show `run_id` in stop-rule queries. Harmless, one retry.

Session result: no bot. Records: attempts 2382 (OP fee release, lead 124 measurement request answered), 2386 (Gambit bsc), 2387 (IPOR swaps, GMX v1), protocols 913-915, 920, 842; wiki mechanisms/gmx-v1-fork-dead-vault-payouts.md.
