# waiting bots: answered (human, 2026-11-13)

- gearbox-v3-watcher-ethereum: the human changed CYCLE_MS in the live bot.js from 20000 to 120000 and ran gate restart (2026-11-12 22:2xZ). Shortest measured window is 34 blocks, so 120 s keeps a margin; expected about 0.22M CU/day.
- franken-dutch-ethereum: left as is. POLL_S 60 stays, because the price reaches zero 2 minutes after ChallengeStarted (phase 60 s) and a longer poll would detect it too late. No rebuild on the feed for now (0.17 USD/day does not pay back a new deployment).
- The live franken bot reads the right emitter: the address it filters on is the one attempts recorded as the true ChallengeStarted emitter.
