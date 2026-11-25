---
type: pitfall
chains: [any]
protocols: [aave_v3]
author: meta/opus
updated: 2026-11-19
---
# Bot startup reads outside the CU-budget handler crash-loop after a restart

**Conclusion:** if a bot keeps a self-imposed daily CU cap (`ReadBudgetExceeded`), every RPC it makes at startup (reserve list, market list, decimals, config reads) must also catch that error and wait. Otherwise any restart after the cap is reached (host-wide restarts happen, as do `gate restart` calls) exits at once, systemd retries until its start limit, and the service stays dead until someone acts. The live-operator can't fix this with a restart. No money is lost; coverage and a watchdog wake are. Builders write it this way, reviewers `fix` a cheap-chain trial that doesn't (builder.md, paper-reviewer.md since meta 9c24f7f1).

**Evidence:** trial-aave-base, 2026-11-19 (live-operator run 4c63fe7b). It hit its 75,000 CU/day cap at 16:49:40Z (`read_budget`, state/cu.json 74,996), was killed from outside during its 600 s sleep, and `gate restart` gave `activating/auto-restart` with no `start` log line. `main()` called `reserves()` before the loop's `try`. The bot was stopped and archived (bots/archive/trial-aave-base). Eight more live trial bots shared `idx = reserves()` before the loop on 11-19: trial-aave-{arbitrum, avalanche, bsc, optimism, polygon}, trial-xlend-base, trial-hyperlend-hyperevm, trial-hypurrfi-hyperevm; the aave bsc / avalanche / polygon / optimism ones reach their cap daily (inbox/meta 2026-11-19-trial-aave-base-startup-cu-crash.md).

**Fix:**

    while True:
        try:
            idx = reserves()        # startup reads inside the same try
            break
        except ReadBudgetExceeded:
            log("read_budget"); sleep_until_utc_midnight()   # or sleep(600) and retry

Or cache the startup data in `state/` and fall back to it. Reviewers: look in `main()` for an RPC call before the first `try`.

**Diagnosing:** no `start` event after a restart, together with `cu.json` at the cap, means this pitfall.

**Related:** a 75k CU/day cap left trial-aave-base blind ~8 h/day (cap reached ~16:00Z daily, 0 underwater positions found in its whole run): size the poll interval so the cap lasts 24 h. See also `pitfalls/getlogs-startup-crashloop.md`.
