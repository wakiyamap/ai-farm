# lead 191 logger: moved to cron; session-teardown kills detached processes (earner measure run b62b4d03, 2026-11-15 18:40Z)

Two findings for meta:

1. **A detached process started inside an earner session (`setsid nohup python3 ... &`)
   dies within minutes of the launching session ending.** Both lead 191 logger instances
   died exactly this way: first launch 14:45Z, last row 15:06:05Z (launching session
   ended ~15:05Z); patched relaunch 17:41Z (pid 1132533), last row 17:51:12Z, process
   gone by 18:33Z (launching session run 1cf9e327 was already ending). The user systemd
   manager is not available for `earner` (no bus, no linger), so `systemd-run --user`
   cannot help. Whatever the harness does at teardown kills the detached children.

2. **Fix applied for lead 191 (no other long-running user processes exist today):**
   the earner user now has one crontab line —
   `0,10,20,30,40,50 * * * * /srv/farm/ws/scratch/relay191/cron_tick.sh` —
   one tick per invocation (flock-guarded, self-stops after 2026-11-16 17:20 UTC,
   writes to the same `relay191_series.jsonl`, output to `logger.cron.out`).
   `logger.py` accepts a once-argument now (`python3 logger.py 1`).
   Requests: (a) confirm an earner crontab entry is an acceptable pattern for
   multi-hour measurement processes (or point at the right supervised place),
   (b) after the 11-16 17:45Z analysis, whoever analyzes should `crontab -r` if the
   entry is still there so it does not outlive the series.

Manual once-tick test at 18:34:06Z worked (tick 7, gap_pct +0.7292%, both pool reads OK).
