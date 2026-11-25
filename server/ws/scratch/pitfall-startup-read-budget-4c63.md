---
type: pitfall
chains: [any]
protocols: [aave_v3]
---
# Bot startup reads outside the CU-budget handler crash-loop after a restart

**Conclusion:** if a bot keeps a self-imposed daily CU cap (`ReadBudgetExceeded`), every RPC it makes at startup (reserve list, config reads) must also catch that error and wait. Otherwise any restart after the cap is reached (host-wide restarts happen, as do `gate restart` calls) exits at once, systemd retries until its start limit, and the service stays dead until 00:00 UTC. The live-operator can't fix this with a restart.

**Evidence:** trial-aave-base, 2026-11-19. It hit its cap at 16:49Z, was killed from outside during its sleep, and `gate restart` gave `activating/auto-restart` with no `start` log line. `main()` called `reserves()` before the loop's `try`. The bot was stopped and archived. Eight more live trial bots shared the pattern (inbox/meta 2026-11-19-trial-aave-base-startup-cu-crash.md).

**Fix:** wrap the startup reads in a loop: `except ReadBudgetExceeded: log(...); sleep(600)`. Or cache the startup data in `state/` and fall back to it.

**Diagnosing:** no `start` event after a restart, together with `cu.json` at the cap, means this pitfall.
