# Phase 14a: builders replace earner-claude and the researchers; reviewers split by model (human, 2026-11-17)

## What changed

- New role `builder` (`roles/builder.md`, about 16 KB). Two instances, OS user harness:
  - `builder-claude` (claude, `claude-mythos-5-2`), timer 00:40 JST and every 3 hours
  - `builder-codex` (codex, `gpt-6-sol`), timer 02:10 JST and every 3 hours
  A builder picks its own target (or one from the queue), checks it, proves it on the fork and places the paper
  bot in one session. Trial bots (decision `2026-11-17-cheap-chain-trials.md`) are written into builder.md.
- Researchers are absorbed: `farm-researcher-claude.timer` and `farm-researcher-codex.timer` are disabled (the units
  and researcher.md stay, so the human can turn them back on). Idea finding, bot census and `ledger add-source` are
  now the builders' job (builder.md section 1, item 6).
- `farm-earner-claude.timer` is disabled: builder-claude takes its place. The earner-claude instance stays.
- Second reviewer: `paper-reviewer-claude` (claude, opus, same `paper-reviewer.md`), every 90 minutes. The
  review-queue context now routes bots: author naming gpt/codex -> paper-reviewer-claude; every other bot
  (Claude, Qwen, unknown) -> paper-reviewer (codex). Rows for the other instance show `other-reviewer`.
- `earner-local` and `earner-measure` (Qwen) are unchanged for now. The next phase replaces them with `scout`
  instances that measure one candidate each from a script-made list.

## What the human asks of you

1. builder.md is yours to maintain like the other role files. The human's direction for this phase: **cut rules
   rather than add them.** Keep builder.md at or under about 18 KB; a new rule should replace an old one or move
   to the wiki.
2. Write `pitfalls/signer-my-address-dict.md` (builder.md links it; see `inbox/meta/2026-11-17-human-bold-live-patch.md`).
3. paper-reviewer.md: add one line about the routing (review only rows that are not `other-reviewer`), and the
   trial-bot review rules if not done yet.
4. From your next report on, per instance (builder-claude, builder-codex, earner-local, earner-measure): sessions,
   outcomes, bots placed, bots promoted, trial bots live with sends, wins and net. And whether builders repeat
   classes already closed (the researchers' old problem).
5. If the builders' sessions mostly end `no_target`, say so: that is the signal for the scout phase.
