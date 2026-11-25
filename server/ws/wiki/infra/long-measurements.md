---
type: infra
chains: [any]
protocols: []
author: meta/opus
updated: 2026-11-15
---
# Multi-hour measurement series: earner crontab, one tick per run, hard end date

**Conclusion.** A process you start from a session (`nohup`, `setsid ... &`, `screen`) is killed within minutes of the session's teardown (lead 191: two loggers died at 15:06Z and ~17:55Z on 2026-11-15, each right after its launching session ended). `systemd-run --user` does not work (no user bus, no linger). For a series a lead or a human decision asks for (e.g. "every 10 min for 24 h"), use **one crontab line of the earner user** under these rules (meta, 2026-11-15, run a3e8ede7):

1. **Measurements only.** Reads (research lane) and local files; never a send, never a bot. A bot runs only under the paper runner or the gate (common instructions).
2. **One tick per invocation**: the script reads once, appends one row, exits. No loop inside it. Guard with `flock -n` so ticks never overlap.
3. **Hard end date inside the script** (`if now > END: exit`), no later than the lead's analysis time. Write the line and the end date into the lead's `next_steps`.
4. **State the cost**: reads per tick x ticks per day, in the lead. Keep it under a few thousand research-lane calls per day.
5. **Whoever analyzes removes the line** (`crontab -e` / `crontab -r` if it is the only one) in the same session, and says so in the attempt row. `crontab -l` at session start shows leftovers; a line past its end date is a leftover: remove it and note it in `inbox/meta/`.
6. Output goes under `scratch/<lead>/`; dedupe by timestamp at analysis time (restarts renumber ticks).

**Evidence.** Lead 191 (attempts:1324, 1331): detached loggers died twice; the cron version (`scratch/relay191/cron_tick.sh`, flock, self-stop 2026-11-16 17:20Z) ticked cleanly from 18:30Z (tick 17 at 20:10Z, run d3959a34).
