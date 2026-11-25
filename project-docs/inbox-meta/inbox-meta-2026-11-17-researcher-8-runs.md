# Earner throttle not adopted; researcher goes to 8 runs a day (human, 2026-11-17)

Answer to inbox/human/2026-11-16-meta-earner-idle-update.md section 1.

## 1. The earner start rate stays as it is

- The human read the numbers (73 earner runs on 11-16, 34 `no_target`) and decided not to throttle the earner.
  The earner runs on the local model, so an idle run costs almost nothing, and throttling would not add income.
- Your two earner.md sentences (no attempts row for a bare queue walk; skip steps 1-4 when the lane's last report is
  `no_target` under 60 minutes old with nothing changed) stay. Keep counting them as you planned.
- Please do not raise the throttle again unless something new makes idle runs harmful (for example they delay real
  work, or they start costing relay CU).

## 2. Researcher: 8 runs a day from 2026-11-17

- New leads now come almost only from the researchers, so the human adds one run to each instance.
- Schedule (JST): researcher-claude 01:10, 07:10, 10:10, 16:10; researcher-codex 04:10, 13:10, 19:10, 22:10.
  That is one researcher run every 3 hours.
- The human changes the timers (drop-in `fourth-run.conf`). Nothing for you to change.
- For your next reviews, please report to inbox/human: leads per researcher run before and after the change, and how
  many of the new leads the earner closed as a repeat of a class that was already closed. If the extra runs mostly
  produce repeats, say so and the human will take them back.

## 3. Unchanged

- No candidate classes from the human in this note. Limits, L, the 400 USD per bot cap, the holding frame and the
  send routes are unchanged.
