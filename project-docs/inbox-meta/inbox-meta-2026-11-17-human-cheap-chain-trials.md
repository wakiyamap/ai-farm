# Live trials on cheap chains (human, 2026-11-17)

Decision: `decisions/human/2026-11-17-cheap-chain-trials.md`. Please read it in full; this note is the summary and
what the human asks of you.

## Why

- Over 200 leads in two weeks, almost all closed as "someone takes it first", and almost no live sends. The first
  earner-claude session (run 3fa7205c) found a new class in 7 minutes and closed it the same way: HAI OracleJob on
  optimism, 22 USD/day gross, taken in the first eligible block (attempts:1439).
- So the limit is the rule, not the model. On a chain where a lost attempt costs cents, the farm now measures its win
  rate by sending, not by counting past windows.

## What changes (trial bots only)

- A trial bot: not on ethereum, `capital_usd` <= 20 (that is its whole loss budget, no top-up),
  `max_loss_per_tx_usd` <= 1, id `trial-<target>-<chain>`, `strategy` starts with `trial:`, reads <= 100,000 CU/day,
  waits on the feed `/logs` or a timer.
- Waived for trial bots: principle 2 (latency races), earner.md section 3 items 3 (reaction time) and 4 (EV), the
  1 USD/day floor, the EV-vs-CU test, natural paper captures and paper waiting time.
- Still required: open to anyone, evidence that someone was paid in the last 7 days and one gross exceeds one
  attempt's gas, the fork proof (success and revert), the executor rules (atomic, reverts unless the balance grows),
  a coded send condition, per-send logs. X, n, L and S are unchanged. No mempool watching, no front-running of other
  users' pending transactions; bidding a priority fee for a public reward is in scope.
- Up to 10 trial bots live at once (200 USD in total), separate from the next-block and one-shot allowances.
- First one: HAI OracleJob on optimism. Then non-ethereum leads and attempts that are `blocked_infra` for speed.
- End: after 7 days or when the capital is spent, results go to `attempts` and to inbox/human through you. The human
  stops bots.

## What the human asks of you

1. Put sections 1-4 of the decision into `roles/earner.md` and `roles/paper-reviewer.md`. Earners read decisions for
   3 days only, so this has to be in the role files before 2026-11-20.
2. `earner.md` is at 55,873 bytes. Move at least as much as you add to the wiki. The reaction-time and EV rules now
   apply to ethereum only, so they can shrink to a line each with a wiki page.
3. `tools/manifest-check.py`: when `strategy` starts with `trial:`, check chain != ethereum, `capital_usd` <= 20 and
   `max_loss_per_tx_usd` <= 1. A warning is enough.
4. From your next report on: trial bots live, sends, wins, net, per bot.

## Unchanged

- ethereum bots, the holding frame, private sends, one-shot leftovers, the 400 USD cap for non-trial bots.
