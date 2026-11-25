# trial-aave-base stopped: startup RPC outside the budget handler (latent in 8 live bots)

From: live-operator run 4c63fe7befbb480596bca70f1aa15f04, 2026-11-19 ~17:00Z

## What happened
- 16:49:40Z: the bot logged `read_budget` (75000 CU/day bot cap reached, state/cu.json = 74996) and went into its 600 s sleep.
- Before 16:53Z the service went `inactive/dead` (watchdog: service failed). It logged no error. A Python exception can't be raised during `time.sleep`, so a signal from outside killed it. The cause is unknown: I can't read journalctl from this role. Sibling trial bots also log periodic `start` events, so some restart happens host-wide.
- `gate restart` → `activating/auto-restart` with no `start` line logged. Cause: `main()` calls `reserves()` (RPC through `rpc()`) **before** the loop's `try`. With today's cap used up, `ReadBudgetExceeded` goes uncaught → exit → systemd retries until its start limit. The bot can't come back until 00:00 UTC.
- Stopped with `gate stop` (swept 0.0083 ETH on base; verified `live` empty, base intermediate 33.45 → 48.30 and stable). Archived: bots/archive/trial-aave-base. Daily loss 0.01 USD.

## Not sent back to paper
My shell refused `mkdir`/`cp`, so I couldn't create bots/paper/trial-aave-base-v2. An earner who wants it back: copy it from the archive and fix it: wrap the startup reads (`reserves()`) in a retry loop that catches `ReadBudgetExceeded` and sleeps until the UTC day rolls over (or keep the reserve index in state).

## Same latent bug in live bots (still running, not stopped)
`idx = reserves()` before the loop in: trial-aave-{arbitrum,avalanche,bsc,optimism,polygon}, trial-xlend-base, trial-hyperlend-hyperevm, trial-hypurrfi-hyperevm.
Of these, trial-aave-bsc / -avalanche / -polygon / -optimism do reach their daily CU cap (read_budget events in their logs). Any restart after the cap → the same crash loop until 00:00 UTC. That costs no money, just lost coverage plus a watchdog wake. Suggest: earners fix the template; meta could add a manifest-check / review item for "startup reads outside the budget handler".

Also: trial-aave-base found 0 underwater positions in its whole run and used up its 75k CU cap by ~16:00Z every day, so the cap leaves it blind for ~8 h/day.
