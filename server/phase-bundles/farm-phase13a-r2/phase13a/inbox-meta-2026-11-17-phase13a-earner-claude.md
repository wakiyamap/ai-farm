# Phase 13a: a third earner instance, on Claude (human, 2026-11-17)

- New instance `earner-claude`: role `earner`, harness `claude`, same role file (`roles/earner.md`),
  OS user `harness`. `/opt/farm/context/earner` gives it the `build` lane (its name does not end in
  `-measure`). Timer `farm-earner-claude.timer`: 8 sessions a day, 00:40 JST and every 3 hours.
- Why: a one-day measurement. The human wants to know what a stronger model does with the same
  earner instructions: how much of the weekly plan limit one session uses, how many sessions reach
  `paper_placed`, how often a tool call is refused. Nothing else changed: same rules, same gate.
- `earner-local` and `earner-measure` (Qwen) keep running as before. Claims keep the three apart.
- Its tool list is in `run-role` (`earner)` case). It cannot `gate promote` or `paper archive`.
  If a session report or the journal shows a refused tool call that the earner role needs, write
  the exact command to `inbox/human/`; the human widens the list.
- Please report to `inbox/human/` after its first 8 sessions: per session the outcome, the target,
  tokens and cost from the runs table (`instance = 'earner-claude'`), any refused tool calls, and
  the same numbers for `earner-local` over the same hours. Do not edit `roles/earner.md` for this
  instance alone; the comparison needs the same file.
