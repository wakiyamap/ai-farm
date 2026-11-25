# Review noise and two small process fixes (human, 2026-11-17 10:3x JST)

1. **`executor armed` reports**: since phase 14 the reviewers wrote six inbox/human notes that a live bot has no
   `executor armed` line, each time for a bot that has no setup transaction. That line is required only when the
   executor needs a setup tx at startup (decision 2026-11-15-executor-no-baked-targets). Please change
   paper-reviewer.md: after a promote, check that the live start line shows the executor address from
   `state/executor.json`; require and report a missing `executor armed` line only when the bot's code sends a setup
   transaction. No inbox/human note when everything matches.
2. **A `wait` for a human funding decision is never re-reviewed** (`next_review_at: null`): trial-morpho-cbbtc-base
   waited after the gate refused for lack of Base gas. The human has since funded Base (47.64 USD) and touched its
   manifest so it shows as CHANGED. In paper-reviewer.md, a funding `wait` should set `next_review_at` to a time
   (e.g. +2 h) so it is retried without the human.
3. **review.md in live copies**: newest decision first (inbox/meta/2026-11-17-promote-review-order.md). Agreed.
4. In your next report: per trial bot, sends / wins / net, and the reason for each loss (blocks late, fee short).
   Six trial bots are live; the human wants to know whether any of them wins at all before 11-24.
