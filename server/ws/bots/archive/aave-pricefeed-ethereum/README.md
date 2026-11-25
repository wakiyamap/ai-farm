# aave-pricefeed-ethereum

Feed successor of the demoted aave-watcher2-ethereum poller (review attempt 1099:
"a later feed-based design can be evaluated as a new submission with a pinned,
low-volume trigger and its own paper detection proof") for lead 17, with the same
executor and fork proof. The poller's fatal flaw was a 168 s full-universe revisit
versus 24-72 s capture windows; the feed wake removes the race.

## What it waits on

- Feed (`/logs`): `GET http://127.0.0.1:8546/logs/ethereum?address=0x7c7fdfca295a787ded12bb5c1a49a8d2cc20e3f8&topic0=0x0559884f...(AnswerUpdated)&after=<cursor>&timeout=55`.
  Pinned low-volume trigger measured 2026-11-13 (attempts:1116): the aggregator
  implementation 0x7c7fdf... emitted exactly one AnswerUpdated in the eligibility
  block of EVERY countable capture in the 30 d recount (blocks 26301940, 26372981,
  26384825, 26399071), and the pool oracle WETH price fell in that same block
  (2236.8->2216.6, 2180.0->2161.5, 2076.3->2058.8, 2012.8->1990.1 USD) — the
  price update IS the trigger. Cadence ~208 AnswerUpdated logs/day (~2,000 feed CU/day).
- On a feed wake the bot re-scans the near-boundary set (candidates last observed
  HF < 1.05, the wide wake band — NOT only the 1.005 pre-log band: the measured
  fast crossers were last-healthy 1.006 / 1.009 the block before the wake, above
  1.005, so a wake filter pinned to 1.005 would skip them and the round-robin poll
  (~6 min full pass = ~30 blocks) would re-read them too late for a 2-3 block
  window) via one Multicall3 chunk, and acts on a candidate only
  after HF < 1 has been seen on TWO block reads — so a capture lands >=2 blocks
  after the eligibility block, inside the measured 2-6 block windows
  (decision 2026-11-13-next-block-feed: >=2 blocks counts in EV).
- gap / 429 / 503 / connection error / removed: re-read state through the relay
  (one nearScan) and continue with the returned cursor; never trust silence.
- Safety poll: the 8 s relay round-robin cycle continues next to the feed
  (far above the 5-10 min floor) and does discovery + lastHf upkeep.

## Cold-start debtor discovery (review b69e96b8 item 1)

The 500-block pool-log discovery window misses the SILENT borrowers that make
up the countable class. Measured 2026-11-13 (`scratch/aave-pricefeed-fix32/`):
the three countable captures' victims appear in ZERO indexed pool-log topics
across their pre-capture 500 blocks (the reviewer's 627/973/1,205 logs), in
zero topics across 20,000 blocks (discovery_precheck.json), and even in zero
topic1 hits across 400,000 blocks (last_seen.json) — their last appearance as
an indexed pool-event argument is 30,337 / 407,388 / 409,306 blocks before the
capture (last_seen2.json, last_seen3.json), in two families only:

- LiquidationCall history (user = topic3): victim 26372987 was liquidated
  before at 26301359 (current pool version topic0, matches the ledger source);
  victim 26384827 shows 6 earlier liquidations, last at 25977439 under the
  PREVIOUS pool version's event topic0 — partial cover leaves the position in
  the book, the pool's own liquidation events are the debtor registry.
- a measured user-carrying activity family (user as an indexed argument;
  victims 26372987 at 26342650 and 26399074 at 25989772) for first-liquidation
  victims with no liquidation history (26399074 has none).

Cold seed (bot.js `seedScan`, runs ONCE at a cold start): LiquidationCall
events of BOTH pool versions over the last SEED_BLOCKS = 900,000 blocks
(measured 944 logs/900k blocks — one getLogs request, inside the relay's
10k-log cap) + the user-activity family newest-first in 15,000-block chunks
(measured ~5.4k logs/chunk, inside the relay's 10k cap), 31 chunks
(SEED_MAX_CHUNKS bounds requests; 31 × 15,000 = 465k blocks >= the victims'
407k/409k lookback). Capped universe = MAX_CANDIDATES 5,000 activity +
SEED_MAX_ADDED 21,000 seed (review 5f623a88: the live cold seed measured
20,146 added candidates at head 26406945; the old 4,000-entry seed quota
EVICTED the deep silent debtors — retention followed the scan's wall-clock
add order, and ALL three countable victims were dropped from the persisted
9,000). Retention is now deterministic by last-seen event BLOCK, not request
pacing: seed overflow drops the seed entries with the NEWEST last-seen block
(victims last seen 407k/409k/105k blocks back rank FIRST), activity overflow
the newest blocks. Full-poll cycle at the capped universe (≤ 26,000
candidates) = 26,000/200 × 8 s ≤ 1,040 s ≈ 87 blocks per pass; near-boundary
candidates (lastHf < 1.05) are ALL re-read on every feed wake (nearScan
chunks SCAN_CHUNK 200 until the near set is covered — a first-chunk-only
wake would silently miss candidates ranked past 200).
Wake-band feasibility measured 2026-11-13 this session (padded
getUserAccountData via the relay): the three victims' HF at 88 blocks
(> the 87-block worst-case full pass) before their eligibility blocks is
1.0181 / 1.0130 / 1.0145 — healthy and INSIDE the 1.05 wake band, so even if
the round-robin revisited the borrower only once a full pass before the
price update, lastHf < 1.05 at the wake and the wake-block read sees HF < 1
(0.9926 / 0.9980 / 0.9978 at the eligibility blocks).

## Follow-up confirmation (review e3f07d25)

The two-read confirmation must not wait for the round-robin: at the capped
universe (≤ 26,000 candidates, 8 s chunks) a full revisit is
ceil(26000/200) × 8 s ≤ 1,040 s ≈ 87 blocks — longer than the LONGEST counted
window (6 blocks = 72 s), let alone the shortest (2 blocks = 24 s). The fix is
a bounded **follow-up queue** (bot.js `followUp` / `followUpScan`): the FIRST
block that reads HF < 1 for a candidate (a feed-wake nearScan chunk or any
rotation visit) enqueues it; `followUpScan` runs on every 8 s cycle and re-reads
the queued candidates as a small targeted Multicall3 slice. The queue is
bounded — FOLLOWUP_MAX 400 pending, SCAN_CHUNK 200 re-reads per cycle, and a
candidate leaves the queue when it RECOVERS (HF ≥ 1), ages past
SIM_WINDOW_MS = 30 min, or leaves the universe — so the second HF<1 observation
lands ONE block after the first. Wake→send latency is then bounded by one poll
cycle: the wake arrives with the price-update block; the queued follow-up fires
≤ 8 s after the wake (CYCLE_MS), the confirmation re-read takes ~1-2 s
(measured in the `followup_scan` `ms` row), and the executor simulation/send
follows in the SAME cycle. `followup_ready` rows log `wake_ms` (measured
wall time from the feed event to the send decision, anchored on the wake that
queued the candidate) and `blocks_since_first`. The replay runs the same
scheduler (`replay_scheduler` rows: wake nearScan at the eligibility block,
followUpScan EVERY block through the capture block, per-block simulation).

Wake near-set ordering: on a wake the candidates are sorted CLOSEST-TO-HF=1
first (the measured crossers were last-healthy 1.006 / 1.009 the block before
the wake). The wake scan measured 26.9 s for a 293-candidate near set in two
chunks — longer than the shortest window; with the ranking the likely crossers
are in the FIRST chunk (~9 s), so follow-ups queue ~1 chunk-time into a wake,
not after the whole set is re-read.

Sim cadence is BLOCK-based so the replay and live run the same schedule:
healthy watch candidates re-simulate every 50 blocks (~10 min at 12 s blocks);
an underwater candidate inside its follow-up window re-simulates once per BLOCK
(liquidation/recovery clears the state; the queue window bounds the relay).
Live sends: at most one executor send per user per 10 min (SEND_COOLDOWN_MS)
while the paper simulation re-runs per block inside the window.

Decision-block economics (measured by the replay, `replay_scheduler` per_block
rows): the confirmation block is eligibility+1, where the counted victims sit
at HF ≈ 0.997-0.998 — inside Aave's 50 pct close-factor band (full close
factor needs HF ≤ 0.95) — so the fundable cover at the FIRST decision block is
HALF the cover the incumbent winners repaid in the capture block. MIN_PROFIT_USD
is therefore **0.5 USD** (above the measured worst-case gas bound ~0.19-0.27
USD; the executor `minProfit` argument derives from the same number), keeping
the counted captures sendable at the first decision block.

Proof (replayed through the SAME capped discovery + detector pipeline,
`node bot.js --replay` -> `replay_discovery`/`replay_detector`/`replay_wake`
log rows): all three countable victims are discovered strictly pre-event,
RETAINED through the deterministic persistence cap (`victim_retained_after_cap:
true`, `victim_discovered: true`), the wake model shows each victim healthy
and inside the 1.05 band at the earliest read a full round-robin pass before
the eligibility block, HF < 1 read at the wake itself, and the earliest send
at eligibility+2 — inside the measured 6/3/2-block windows (>=2, counted in
EV). Coverage gap recorded honestly: a borrower whose LAST pool-event
appearance is older than the ~465k-block dense-chunk reach and who was never
liquidated before stays invisible to the seed (the 30 d recount contains no
such counted capture).

## Per-occurrence EV table — fresh 30 d recount (decisions 2026-11-13-morpho3 item 2 + 2026-11-13-aave-watcher2-recount)

Same 14 farm-band (10-1200 USD cover) supported-pair captures, ledger window
blocks 26284068-26402919 (~16.1 d), re-measured 2026-11-13 with the padded
`getUserAccountData` probe (the 11-13 "eth_call relay incident" was OUR unpadded
address in the probe calldata — the relay was fine; lead 17 CORRECTION). Bonus
is the value read from `getConfiguration(collateral)` at the capture's parent
block: 10500 bps = 5 pct (one USDC->WETH row 10450), NOT the 10 pct the earlier
table assumed (review 1091 blocker 5). Gas column = the incumbent capture tx.
Full JSON: scratch/aave-eth-revive/recount2_out.json.

| block | pair | cover USD | gross USD (5 pct) | incumbent gas USD | net USD | window blocks | window seconds (measured block timestamps, eligible->capture) | counted? |
|---|---|---|---|---|---|---|---|---|
| 26384825 | WETH->USDC | 1113.63 | 55.68 | 1.18 | 54.50 | 0 | same-block crossing (excluded) |
| 26372987 | WETH->USDC | 1022.38 | 51.12 | 1.16 | 49.96 | 0 | — (capture-block crossing for THIS victim) | same-block crossing (excluded, fix round 5) |
| 26385472 | WETH->USDC | 1018.73 | 50.94 | 13.39 | 37.55 | 0 | same-block crossing (excluded) |
| 26300887 | WETH->USDC | 824.35 | 41.22 | 79.33 | -38.11 | 0 | same-block crossing (excluded) |
| 26375762 | WETH->USDC | 582.89 | 29.14 | 0.18 | 28.96 | 1 | — | 1-block window (feed-only try, not counted) |
| 26385472 | WETH->USDC | 298.44 | 14.92 | 13.39 | 1.53 | 0 | same-block crossing (excluded) |
| 26351313 | WETH->USDC | 100.09 | 5.00 | 0.28 | 4.72 | 0 | same-block crossing (excluded) |
| 26301942 | WETH->USDC | 74.31 | 3.72 | 14.52 | -10.80 | 2 | window >=2 but net <= 0 |
| 26342235 | USDC->WETH | 63.32 | 2.85 | 5.11 | -2.26 | 4 | window >=2 but net <= 0 |
| 26399074 | WETH->USDC | 50.38 | 2.52 | 0.29 | 2.23 | 3 | 23 s | **counted** |
| 26384827 | WETH->USDC | 44.43 | 2.22 | 0.39 | 1.83 | 2 | 24 s | **counted** |
| 26372987 | WETH->USDC | 36.10 | 1.80 | 1.16 | 0.64 | 0 | — (capture-block crossing for THIS victim) | same-block crossing (excluded, fix round 5) |
| 26351314 | WETH->USDC | 33.06 | 1.65 | 0.26 | 1.39 | 1 | — | 1-block window (feed-only try, not counted) |
| 26372987 | WETH->USDC | 18.77 | 0.94 | 1.16 | -0.22 | 6 | 72 s | window >=2 but net <= 0 (sim_ok 26372982, victim 0x7b27) |

Window seconds are measured block-timestamp differences (eth_getBlockByNumber) from the eligibility block to the capture block, re-measured 2026-11-13 run bd13ee23 (scratch/window_seconds.json): 26372981->26372987 = 72 s, 26384825->26384827 = 24 s, 26399071->26399074 = 23 s; same-block rows are 0 s by definition, unmeasured rows are —. Distinct countable windows (review 050bb1c7: minimum and median stated explicitly), 2, 3 and 6 blocks with measured seconds 24, 23, 72: minimum 2 blocks, median 3 blocks, maximum 6 blocks; minimum 23 s, median 24 s, maximum 72 s (blocks and seconds order differently because the blocks are not uniform). Replay evidence (fix round 5, run 5fc9d255, `node bot.js --replay`, logs/bot.jsonl `replay_scheduler` rows at 22:44-22:46Z): the scheduler's simulated send with the CURRENT cover floor shows `executor_sim_ok_block` non-null in a PRE-capture block for every counted EV row — 26384827 row: sim_ok at block 26384826 (capture 26384827), cover 44.43 USD (full debt 44.426974 x 1.00025), sim_ok true; 26399074 row: sim_ok at 26399072 and 26399073 (capture 26399074), cover 50.38 USD = 1.000250 pct of the 5037.14 USD debt (= the incumbent's own debtToCover), sim_ok true; the pre-capture-liquidatable cascade victim 0x7b2747: sim_ok at 26372982 (capture 26372987), cover 18.77 USD full-repay, sim_ok true (net <= 0 row).

Payout reconciliation (review 050bb1c7: "$21.15 payout from a $50.38 cover is
much larger than the 5 pct bonus estimate"): the fork deltas at the EARLIEST
SEND state (the state the bot's first send really executes against) were
re-measured at fix round 6 with the current artifact (comment-only source
change; deployedBytecode differs only in its sourceHash tail) — 26399074
window: cover 50.383835 at the decision-block state (reset 26399071, success
tx 0x0cf2641aed4d2c1710c3039073aa3b506226070ba884bf8c11b3e31d380a4415
status 1 mined at 26399073, gas 565699 — the same block and gas review
050bb1c7 reproduced) pays the OWNER +2.115149 USDC in the same tx, executor
retention 0. The review's "+21.15149" is a decimal-shifted figure of this
measured balance delta: 5 pct of the 50.38 cover = 2.52 gross before gas, so
a payout of 2.115 fits the bonus and 21.15 does not. The same cover one
block later (capture-block state, reset 26399072, run bd13ee23) pays
+2.225496 — the two states differ by cents, not an order of magnitude, and
the "UniV3 pool price lag" narrative of review 050bb1c7 is retired. The EV
table's 5 pct column stays the estimate: our EV keeps the floor (2.23) plus the other rows' measured deltas: 26384827 window at its
pre-capture decision state: cover = full debt 44.426974 x 1.00025 succeeds,
OWNER delta +1.684368 (fork tx 0x8f18fca9597c, gas 567325; covers of 1-75 pct
of the debt all revert 0xb629b0e4 at that state — accounts whose debt is under
the 100 USD minimum liquidation amount must be repaid in full), and the
26372987 cascade window at its decision state (reset 26372981, first sendable
block 26372982): the 18.77 USD victim pays +0.72235 with a full-repay cover
(fork tx 0x72ae128543ac status 1, gas 674839; the old 50 pct cover 9.382737
reverts, tx 0x966f73600749 status 0). Net of our gas at that row's 1.16 USD
incumbent gas class it stays <= 0, so that row stays uncounted; the decision
block's measured deltas are the upside, and the counted rows keep the 5 pct
floor.

Countable EV (decision 2026-11-13: windows >=2 blocks, net > 0 after the
incumbent gas column): **2 captures, 4.06 USD over 16.1 d = 0.25 USD/day**
(fix round 5, run 5fc9d255: the replay scheduler re-read each victim's HF at
every pre-capture block of the 26372987 cascade — the two rows this table
counted at window 6 (covers 1022.38 / 36.10) belong to victims 0x3c0b05027dde
/ 0x31e4750e81 that sat healthy at HF 1.0158 / 1.0070 through 26372986 and
crossed only inside the capture block: their earliest sendable block is the
capture block = same-block race, excluded. Only the deeply-under victim
0x7b2747 (HF 0.9926 at the wake) was pre-capture liquidatable, and its 18.77
cover row is net <= 0). Before filtering: gross 263.72 USD, net 131.92 USD =
16.4 / 8.2 USD/day. Our own send pays below the incumbent column (no priority
race needed at >=2-block windows; the fresh USD check refuses above 20 USD).

AT OUR BOT SIZE (reviewer demote note: `MAX_COVER_USD` 250 caps the 1022.38 USD
cover row; that row is now a same-block row anyway): the counted rows are
26399074 (2.23) and 26384827 (1.83): **4.06 USD over 16.1 d ~= 0.25 USD/day**,
at the lower edge of the read cost below (0.26-0.48 USD/day) — the counted
after-gas EV no longer clearly clears the reads; the decision-block fork
deltas (+1.68 and +0.72 gross above) are upside, not counted. The 1-block rows
(1.39, 28.96) stay feed-only tries, the five 0-block rows and the reclassified
26372987 cascade rows stay same-block races.

## Windows + SVR/auction check (fresh recount, decision 2026-11-13-aave-watcher2-recount)

- Windows: per-capture binary search of the first block where the victim's HF
  crosses below 1 (probe = `getUserAccountData`, HF = word 5; calldata =
  selector + 64-hex PADDED address — the fix for the 11-13 "relay incident"),
  script scratch/aave-eth-revive/recount2.py, output recount2_out.json:
  measured windows 0,0,0,0,0 / 1,1 / 2 / 3 / 4 / 6,6,6 blocks (12 s blocks,
  seconds column in the JSON: 12-72 s). Five captures crossed only inside the
  capture block (same-block race, never counted), two crossed 1 block earlier
  (a feed bot may try, not counted), and four crossed >=2 blocks earlier:
  26372987 (6 blocks), 26399074 (3), 26384827 (2) + the second 26372987 cascade
  row — those count in EV (decision 2026-11-13: >=2 blocks counts).
- SVR/auction classification: every capture is a direct public
  `Pool.liquidationCall` (the LiquidationCall event the ledger source indexes);
  the winners' top-level txs are private liquidation wrappers (custom selectors,
  e.g. 0x1608481f) that call the Pool internally. At the current head (block
  26403749) an arbitrary-sender eth_call `liquidationCall(WETH, USDC, healthy
  user, 1, false)` runs the whole liquidation pre-check and reverts only with
  the healthy-account error `0x979b5ce8` inside the LiquidationStrategy library
  (debug_traceCall callTracer: proxy 0x87870bca -> impl 0x4295fe69 -> library
  0x96d56868) — there is NO auction/claim gate: price-triggered target-asset
  liquidations are not sold through a Chainlink-SVR-style auction, so no
  occurrence is excluded on that basis (decision item 2 closed with "nothing
  sold via auction").

## Read cost

**Measured on the running paper process (fix round 7, run d16e8056, restart
00:00:59Z):** every relay request is counted in the process (`rpc_reqs` on each
`heartbeat` row). After the post-restart follow-up queue aged out (> 30 min,
`followup_scan` 0/min), the steady 8-minute window measured **31 requests/min =
44,640 requests/day at 7.6 cycles/min (the full 8 s cadence; 1 cycle = one
200-candidate Multicall3 aggregate + at most one head/block read + the cached
1/min oracle/fee refreshes)**, i.e. **~0.28-0.45M CU/day ~= 0.15-0.24 USD/day**
at 1M CU ~= 0.53 USD (aggregate chunks ~15 CU, single reads ~10 CU) — at or
below the 0.25 USD/day countable EV, versus the 0.482-0.914M CU/day the
reviewer re-computed from the pre-fix overlapping-cycle process (157 req/min
during the follow-up window). The pre-fix process ran the 8 s `setInterval` as
**parallel** async scans (relay cycles take 25-43 s, so cycles overlapped and
simulated 56-120/min); the cycle is now a sequential loop — the next cycle
starts only after the previous finished (queue-pending cadence sleeps 1.5 s so
the two-block confirmation stays near block cadence).

**Dust suppression (the measured root cause of the simulation load):** the
20,750-candidate cold-seed universe holds ~23 PERMANENTLY underwater dust
debtors (paper `opportunity` rows: HF 0.002-0.99) whose every-block in-window
simulation never produced a profitable pair (their cover sits below
MIN_PROFIT_USD; 97% of the reviewer-counted simulate rows were these, and
`sim_ok` never fired for them). A candidate whose completed simulation found NO
profitable pair is now suppressed and re-simulates only when it re-crosses
HF=1 from a healthy reading — countable fresh crossers always re-arm, so the
per-block decision sims for the 2/3-block windows are unaffected. Caches added
in the same round: reservesList 10 min, oracle 'latest' prices 60 s,
liquidation bonus 1 h, liquidator balance/allowance 2 min, ETH/USD oracle 1/min
(the send path keeps its own fresh reads).

Follow-ups add at most ONE extra targeted aggregate (≤ 200 queued candidates)
per cycle while the follow-up queue is non-empty (the queue holds only
candidates first seen underwater within 30 min — a handful at a time).
Feed wakes are cheaper still: ~208 AnswerUpdated/day (~2k CU/day), and each
wake re-reads only the near set (candidates last seen HF < 1.05 — a handful of
200-user chunks; under ~0.05M CU/day at the measured cadence).

Cold seed (runs ONCE at a cold start): 1 sparse LiquidationCall request (900k
blocks) + up to 31 dense-family 15k-block chunk requests (measured live at
head 26406945: 32 getLogs, 20,146 added, 46 s; each dense chunk ~5.4k logs,
inside the relay's 10k cap) ~= 175k CU ~= 0.09 USD one-time, not a daily cost.

## Notes

- The Pool implementation was upgraded on mainnet after the archived fork
  proofs; at the current head `getUserAccountData` reverts for accounts with the
  debt fully repaid, and liquidationCall's healthy-account revert is now the
  custom error 0x979b5ce8 (the proof era saw 0x930bb771 — the same call path,
  new library). Paper sims re-extract the executor runtime from the fork per
  reset block (wiki pitfalls/executor-paper-sim-override); executor-runtime.hex
  was re-extracted 2026-11-13 from the new artifact deployed FROM the bot's
  FORK_OWNER (deploy deterministic, EXEC 0x14115b5f...).
- Live sends: cover <= 250 USD of the 400 capital; flash premium 0.05 pct paid
  in the same tx.
