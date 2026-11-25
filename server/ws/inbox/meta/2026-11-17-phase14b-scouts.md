# Phase 14b: four Qwen scouts replace earner-local and earner-measure (human, 2026-11-17)

## What changed

- New role `scout` (`roles/scout.md`, about 4 KB), four instances `scout-1` .. `scout-4` (dsh, qwen3.8-flash-next,
  OS user earner, one llama-server slot each). A scout does not choose: `/opt/farm/context/scout` hands it the
  next candidate from `scout/queue/` (atomic move to `scout/doing/`) with the steps for its kind. It measures, writes
  KB rows and closes the candidate with `scout-done` (to `scout/done/`). 20-minute sessions, a new one a minute
  after the last ends, only while the queue is not empty.
- `farm-scout-enum.timer` (every 2 h, as earner) fills the queue with `/opt/farm/bin/scout-enum`:
  `trial` = non-ethereum `blocked_infra` leads, `actor` = repeated `ledger top` actors with no `actors` row,
  `protocol` = DefiLlama protocols on the farm chains with TVL >= 100k USD and no `protocols` row (cheap chains
  first, newest listings first). Stale `doing/` files go back to the queue (3 tries).
- A scout's good result becomes a `leads` row with `status: measured`; builders already take measured leads without
  a bot (builder.md section 1, item 5). Trial leads it confirms get `TRIAL CANDIDATE:` at the front of `next_steps`.
- `agent@earner-local` and `agent@earner-measure` are stopped and disabled (role file and units kept).

## What the human asks of you

1. `tools/session-report.py`: accept role `scout` with outcomes `scouted`, `no_candidate`, `aborted`, if it does not
   already read them from the role file. Until then scouts append with `>>`.
2. Report per day: candidates queued / taken / closed by verdict, scout sessions and their average length, how many
   scout leads builders took and turned into paper bots. If most protocol candidates come back `no_reward` or
   `not_found`, say which categories, so the enumerator can skip them.
3. Anyone may add a candidate by hand: a JSON file in `scout/queue/` named `5-00000-<id>.json` with `id`, `kind`
   (any word), `chain` and a free-text `steps` field (the context prints `steps` as the instructions). Builders may
   use this to hand measurement work to scouts.
4. Keep scout.md short (under about 5 KB). It is read by a local model: fewer, plainer rules work better.
