# phase 11c follow-up: all three live bots were affected (human, 2026-11-14)

- franken-dutch-ethereum also never had EXECUTOR_ADDR. bot.py reads only the environment variable and, in live mode, sends nothing without it. Its startup lines show exec "" on 2026-11-11 and the deployed address from 2026-11-13T18:35:36Z.
- So before 2026-11-13T18:35Z no live bot with an executor could send: franken-dutch-ethereum and gearbox-v3-watcher-ethereum since 2026-11-09, morpho-nextblock-ethereum since its promotion. The same holds for stopped executor bots that read the address the same way.
- "Live, zero sends" before that time is not evidence against a lead. Where a lead was closed or a bot was stopped mainly on that ground, say so in the next report to inbox/human; do not reopen anything by yourself.
- The 14-day window of the next-block trial (morpho-nextblock-ethereum) starts at 2026-11-13T18:35Z.
- franken heartbeat shows pending {"11": "waiting"}. Earner: one line in the next session report on what that entry is and whether it can still be taken.
