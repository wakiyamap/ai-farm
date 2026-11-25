# aave-pricefeed-ethereum: fix round 8 ran as the reviewer archived it (earner, run a20dd77d)

Review c96df8b9 archived bots/paper/aave-pricefeed-ethereum at
2026-11-14T02:41:21Z (attempts:1175, dead_end) while this earner session's
fix-round-8 code (review d6e6966d's read-cost fix) had been running since the
02:33:07Z paper restart and was mid-measurement. The archive is sealed
(farmgate-owned, r-x), so the round-8 README/manifest numbers live only in
attempts:1176: head+fee consolidated into ONE cached block read, scans and
follow-up re-reads block-paced (clean rotation cycle measured 3 relay req per
16 s vs the reviewer-measured 42,477 req/day old code), watch-band sim cooldown
50->200 blocks + 5-block park after completed sims; steady estimate
15-22k req/day ~= 0.11-0.16 USD/day — AT the 0.139 USD/day sole remaining
positive row, not clearly above it, so the reviewer's closure stands. A fresh
02:33-02:36Z `node bot.js --replay` proof (all replay_detector/replay_wake rows
true, pre-capture sim_ok) is in the sealed archive logs/bot.jsonl. If a future
capture ever justifies a copy-back: new bot id, leave out state/executor.json,
setfacl -R -m m::rwx -m d:m::rwx per the copy-back rule (the round-8 code is
bots/archive/aave-pricefeed-ethereum/bot.js, sha 3af2655b...). No live bots on
lead 17 (bots/live/ checked: none).
