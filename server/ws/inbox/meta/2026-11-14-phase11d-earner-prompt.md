# phase 11d: earner.md rewritten, common.md shortened (human, 2026-11-14)

The human asked for the earner prompt to be tightened. It was 55,874 bytes assembled, 126 below
the warning line, after ten decisions in three days.

## What changed
- `roles/earner.md`: rewritten, 22,924 -> about 18,000 bytes. Every rule was kept; what went is
  history ("lead 72 reached 11 sessions", dates of incidents) and wording that repeated
  common.md. The old file is `/srv/farm/prompts/roles/.earner.md.bak-11d` and in ws/history.
- New first section "Five checks before you trust a result": addresses, selectors/topics,
  positive control for a zero, caller error before "tool is broken", what "takeable" means.
  These are the earner's repeated errors of 11-06 to 11-14, moved to where they are read first.
- Target choice is now one ordered list (unfinished bot, fix bot with its three exceptions,
  census A entry, open lead, something new, no-target work).
- Section 3 "Evaluate" is reordered (open to anyone, farm scale, reaction time, EV, loss,
  legality, fit) and uses decision 2026-11-14-race-rule-seconds. The block-count wording of
  2026-11-13-next-block-feed is gone from earner.md and from common.md Principle 2.
- `common.md`: the chain paragraph is a short list per chain (same facts, plus Base 0.2 s
  blocks); Principle 2 states the race rule by reaction time. 16,387 -> 16,218 bytes.
- TOOLS.md was not touched.

## For meta
- Do not add the removed history back. When a new rule is needed, put the rule in one line and
  the story in the wiki.
- paper-reviewer.md and researcher.md still carry the block-count race wording: replace it with
  the reaction-time rule (decision 2026-11-14-race-rule-seconds), do not add to it.
- Decisions no longer cited by name in earner.md (their rules are still there): 2026-11-04-breadth,
  2026-11-06-loss-usd-basis, 2026-11-06-no-latency-race, 2026-11-10-live-loss-stop-watchdog,
  2026-11-11-moonwell-stopped, 2026-11-12-morpho-stop-researcher-runs,
  2026-11-13-morpho3-stop-ev-net-of-gas, 2026-11-13-next-block-feed. If you find a rule of
  theirs missing, say which in inbox/human; do not restore the old paragraph.
- Measure before and after, per day, for the earner: sessions with outcome no_report, notes in
  inbox/meta that turn out to be caller errors, sessions on a lead past the stop rule, and
  sessions that end with a positive fork delta or a placed bot. Baseline = 11-11 to 11-14.
  Report the comparison to inbox/human after 3 days.
