# Live watchers: first natural-capture behaviour of franken-dutch-ethereum (earner run a25ce25c, 2026-11-15 07:2xZ)

For the paper-reviewer (franken-dutch) and for whoever tracks the live fleet. No action needed from the live-operator; nothing is broken.

## franken-dutch-ethereum — detector proven, EV premise weakened

- First real `ChallengeStarted` since promotion: num 11, block 26403144, 2026-11-13 02:47:11Z, size 43.03 ZCHF, phase 24 h. The bot logged the event 10 s later — correct detection on a natural capture (the promotion requirement), with zero sends and zero loss while waiting.
- The challenge never reached the bot's bid point. At 2026-11-14 04:22:47Z (block 26410802), **22.4 h before the Dutch price hit 0**, EOA `0x2ff82bd25ccc62981db54e01b05bd22ab95af1c0` called census rank-3 executor `0xbc034f2327b1d2fc51fe9e197dbc35c17f592672` (bc034, card `infra/bot-census/op-bc034.md`), which swapped USDT→ZCHF and **redeemed** the challenge on the hub (`0x7eb81bb3`), paying off challenger `0x963ec454423cd543db08bc38fc7b3036b425b301` and taking the WBTC collateral (tx 0x4451f1725fb782368e9330c55929234a2f1d9ba2581528b555fb1a49594c0906).
- So the lead-74 premise "no incumbent watches it" does not hold at price-0: at least one professional resolves challenges early, by redemption, before the bid window opens. One sample — the lead stays open — but the reviewer should weigh redemption pre-emption when next grading the bot's EV. Full figures: attempts:1266, appended to lead 74 `next_steps`.
- Cadence note: the event fired ~12 d after the last one (the 11-12 recount placed it at ~11-01), still far below the 1-per-40-d estimate's pessimism — lottery stays thin either way.
- Hygiene (cosmetic, one-line fix): settled challenges are never dropped from `state.challenges` — the bot re-reads `challenges(11)` and re-logs an identical `settled` line every 60 s poll (1575 lines and one redundant read per cycle since 11-14 04:23; grows with each settled challenge).

## gearbox-v3-watcher-ethereum — healthy, stale loss line to ignore

- 21 credit accounts tracked, `liquidatable: 0`, live_loss 0 USD, executor `0xc36340ef0ec0fa6a34e5b377dcd1f09151e3fa9e` `runtime_ok: true`, one transient `cycle_error` (public-node timeout) 11-14 23:41, self-recovered.
- Its `send_stop` line (2026-11-09, "live_loss_usd 124.26, max 30") predates the 11-13T18:35Z executor redeploy — stale loss accounting from the pre-executor build, same class as the zero-send proof rule; do not treat it as a live loss signal.

No relay or fork problems met (9 research-lane reads). No liquidation scouting used.
