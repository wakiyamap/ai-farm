# phase 12a: a second earner instance in a "measure" lane; decision 2026-11-15-widen-beyond-liquidations applied to earner.md and researcher.md (human, 2026-11-15)

What changed, so you do not re-apply or undo it.

## 1. New instance: earner-measure

- `/etc/farm/roles.conf` has a new line: `earner-measure  earner  dsh  qwen3.8-flash-next`. Same role file (earner.md), same OS user (earner), same local model, a second slot of the LLM server. It runs in a loop like earner-local (75 min sessions, 5 min pause).
- The role is still `earner` everywhere (KB author, session reports, ops.db). Tell the two apart by instance: the session context prints `instance:` and `lane:`.
- `/opt/farm/context/earner` now prints the lane (`measure` for an instance whose name ends in `-measure`, else `build`) and a lane-specific list: the measurement queue (oldest unmeasured leads, 400 chars of `next_steps`) or the measured leads without a bot.

## 2. earner.md

- New "Lanes" paragraph in section 1: `build` takes measured leads first; `measure` runs the oldest unmeasured lead's measurement request as written and never builds (one-shot leftovers excepted).
- The target list lost the crash post-mortem item and the census / rival-executor / re-triage work in "no target left" (closed by the decision). "No target left" now means: end short.
- The liquidation rule lost the census exception. Two new rules: `private-send` tagging, and holding types as leads (paper only until the 200 USD frame exists). Evaluation step 2 points to the holding rule.

## 3. researcher.md

- New first output item: non-liquidation leads written as measurement requests, every run (6 runs a day now: codex 04:10 / 13:10 / 22:10 JST, claude 01:10 / 10:10 / 16:10 JST).
- The liquidator-census and crash-post-mortem items are replaced by one "closed" line. The bot-census item says to stop at which protocol and operation an operator calls. The pull-oracle sentence is its own item.

## What I ask of you

1. The decision's items 1-3 are already in the role files: do not add them again. Its remaining item is yours: write the crash post-mortem summary to inbox/human from what exists, by 2026-11-16.
2. Watch the measure lane for a week and report in the next weekly report: sessions, leads moved from unmeasured to measured / dead_end / blocked_infra per day, how many requests could not be run as written (and why), and whether the two instances ever worked the same target. Count by `run_id` joined to ops.db's instance, not by role.
3. If researchers' requests are too vague to run, fix the wording in researcher.md, not in earner.md.
4. Wiki pages `methods/crash-postmortem.md`, `methods/follow-slow-liquidators.md`, `methods/blocked-infra-feed-retriage.md`: add one line at the top saying the work is closed by decision 2026-11-15-widen-beyond-liquidations, keep the content.
5. Keep the assembled prompts at or under 56,000 bytes, as before.
