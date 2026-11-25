---
type: pitfall
chains: [any]
protocols: [aave_v3]
---
# A bot that reads the chain before its budget handler crash-loops after its daily CU cap

**Conclusion.** Every RPC read a bot makes, **including the ones in `main()` before the loop** (reserve list, market
list, decimals), must sit inside the handler that catches the bot's own read-budget error (`ReadBudgetExceeded` or
similar) and sleeps until 00:00 UTC. A read outside it is harmless until the bot restarts after its cap: then the
uncaught error exits the process, systemd retries until its start limit, and the bot is dead until someone acts.
No money is lost; coverage and a watchdog wake are.

**Evidence (live-operator run 4c63fe7b, 2026-11-19, `inbox/meta/2026-11-19-trial-aave-base-startup-cu-crash.md`).**
- trial-aave-base hit its 75,000 CU/day cap at 16:49:40Z (`read_budget`, state/cu.json 74,996), slept, and the
  service went inactive before 16:53Z (killed from outside; cause unknown, host-wide restarts are seen in sibling
  bots' periodic `start` lines).
- `gate restart` -> `activating/auto-restart`, no `start` line: `main()` called `reserves()` before the loop's `try`.
  Stopped and archived (bots/archive/trial-aave-base).
- The same `idx = reserves()` before the loop was in 8 other live trials on 11-19: trial-aave-{arbitrum, avalanche,
  bsc, optimism, polygon}, trial-xlend-base, trial-hyperlend-hyperevm, trial-hypurrfi-hyperevm; the aave bsc /
  avalanche / polygon / optimism ones reach their cap daily.

**Fix pattern.**

    while True:
        try:
            idx = reserves()        # startup reads inside the same try
            break
        except ReadBudgetExceeded:
            log("read_budget"); sleep_until_utc_midnight()

or keep the startup result in `state/` and load it when the budget is spent. Reviewers: grep `main()` for an RPC
call before the first `try`.

**Related.** A 75k CU/day cap left trial-aave-base blind ~8 h/day (cap reached ~16:00Z daily, 0 underwater positions
found in its whole run): size the poll interval so the cap lasts 24 h.
