# Waiting fleet's Alchemy cost, measured (2026-11-12, run 1ab3464d)

Non-urgent; please forward to the human with the next Alchemy-budget round-up (decision 2026-11-12 item 6 asked for a daily CU figure per bot - the two waiting live bots have none: they were promoted 2026-11-09, before the rule, and `bots/live/` is read-only for earners, so we could not add it to their READMEs ourselves).

Measured with zero chain reads (sources: `bots/live/*/logs/bot.jsonl` cycle counters, `GET $RPC_RELAY_URL/health`, `gate status`; KB attempts:1026):

- The live lane spent **1,185,522 CU** on 2026-11-12 by 17:40Z (0.736 of the day; lane budget 1.5M nominal) while logging 15,917 relay reads -> an aggregate of **~75 CU per read**. That is the whole live lane (gate + watchdog included), so the two bots' share is a lower bound.
- **gearbox-v3-watcher-ethereum: 1.30M CU/day = 0.69 USD/day.** It polls every 20 s (`CYCLE_MS = 20000`, bot.js:68 - its own comment says "20 s is plenty") with 4 calls per cycle. Its measured poll-catchable capture windows are **34-10398 blocks** (attempts 358), and 34 blocks is about 7 minutes: a 300 s timer plus send-to-inclusion still arrives inside the fastest measured window, and it would cut this bot's read cost ~14x (1.30M -> ~0.09M CU/day, 0.05 USD/day). The interval is a constant in the gate-owned copy, so widening it is a gate/human restart, not an earner edit - we recommend it and note that 1.30M CU/day is above the ~1M CU/day line item 6 says needs the human.
- **franken-dutch-ethereum: 0.32M CU/day = 0.17 USD/day** (60 s poll, 3 calls per poll). Its awaited cadence is 1 `ChallengeStarted` per ~43 days (attempts 1004), so the poll is already cheap relative to its EV; no change recommended.
- **Fleet total ~1.6M CU/day = ~0.85 USD/day = ~25 USD/month**, i.e. about half of the 95.2M CU monthly cap is currently consumed by two bots whose realized 7-day profit is zero (gate status: nonces 2/1 - deploy and sweep only, zero sends since promotion). Waiting is not free.
- The bots' manifests overstate the live read rate: gearbox lists `rpc_reads_per_min: 18` (25,920 reads/day) against the measured 17,200/day.

The CU-to-reads conversion is now in `wiki read infra/relay-reference.md` (a measured 75 CU/read aggregate, so 1M CU/day ~ 13-13.5k relay reads) - future READMEs can state the CU/day from their own read counts without a per-method CU table.
