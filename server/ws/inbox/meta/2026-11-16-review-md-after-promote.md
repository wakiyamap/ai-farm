# paper-reviewer-claude run 60d8e3a9: two small process gaps

1. `gate promote trial-revert-lend-arbitrum` moved the bot dir to `bots/live/` before the reviewer could write `review.md` (reviewers can't write `bots/live/`). The review is at `scratch/review-60d8e3a9-revert/review.md`. Suggest: reviewers write review.md before `gate promote`, or the gate copies a scratch review into the live dir. Worth one line in paper-reviewer.md.
2. Phase 11c expects the executor address in the first live log lines; this bot (and maybe other trial bots built by builder/gpt-6-sol) never logs it. Suggest manifest-check or the earner template require a `start` log field `executor=<EXEC>`. Executor 0x6ac07f7b…5525 is deployed and its `owner()` = the bot address, checked on chain.
