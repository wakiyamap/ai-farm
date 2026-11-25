# morpho-nextblock-ethereum (paper)

NEXT-BLOCK TRIAL bot per decisions/human/2026-11-13-blocked-infra-feed-retriage item 3: the same
executor, scan path and payout as morpho-watcher3-ethereum (predecessor of record, reviewer-accepted
fork proofs, bots/archive/morpho-watcher3-ethereum), rebuilt to WAIT ON THE FEED (`farm-feed /logs`)
with a >= 5 min safety poll instead of a 60 s poll, under the trial conditions:

- waits on ONE feed filter (below), safety poll 10 min >= 5 min - YES
- total daily CU 42k steady / ~48k first day <= 50,000 - YES (table below; review b69e96b8 fix 1
  bounded the deep backfill: pinned markets only, 8000-block pages, ~180 one-time getLogs)
- capital_usd 16 <= 20 - YES
- last-30d 1-block capture with gross > 50 USD - YES: the whale block 26384831 (repaid 92,326.04
  USDC, gross ~3,111-4,048 USD at the 4.384 pct convention, attempts:1053)
- the other review gates (fork success + revert, profit to the wallet in the same tx, send only when
  expected gross > gas cap) are the predecessor's, unchanged.

## The trigger, measured this session (run 5292c807, 2026-11-13)

The pinned Morpho oracle wrappers emit NO logs (attempt 1053), so a feed bot cannot wait on them.
The fork trace of the whale capture tx
0x86e8dccc48af1873f7e6999e4684655429b4e1c8bf90ff33162620eb30459701 (block 26384831) shows
Morpho STATICCALLing the WBTC/USDC wrapper `price()` (0xa035b1fe), and the wrapper reading
`latestRoundData()` from three upstream aggregators - the price moves the moment an aggregator
publishes a round; no wrapper update() call is needed. The upstream Chainlink BTC/USD proxy is
0xf4030086522a5beea4988f8ca5b36dbc97bee88c (description() = "BTC / BTC"-pair, measured via
eth_call); the AnswerUpdated logs land on its IMPLEMENTATION (pitfalls/proxy-implementation-no-logs):

    filter: address = 0x4a3411ac2948b33c69666b35cc6d055b27ea84f1,
            topic0  = 0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f
            (= cast keccak "AnswerUpdated(int256,uint256,uint256)")

- measured cadence: 99 AnswerUpdated logs over 3 d at head (blocks 26399047-26406047) = ~33/day.
  The two other WBTC-wrapper aggregators (WBTC/BTC 0xa5e3a55c..., USDC/BTC 0x54bcc589...) and the
  WETH wrapper's ETH/USD aggregator (proxy 0xc0053f... = the aggregator itself, the WETH-side capture
  trace shows NO impl hop; 0 logs over 1 d at head) published nothing over 3 d - they are the
  "pinned" (dormant) feeds; WETH-side accrual crossings are covered by the 10 min safety poll.
- causality of the 1-block class: the BTC/USD AnswerUpdated block 26384830 is C-1 of the whale
  capture (26384831), and the capture tx's wrapper price() read EXACTLY that round (fork trace
  output updatedAt 0x6af31cc8/0x6af31cdb = the publication log's round, measured from the
  implementation's own log row at block 26384830). Farm-feed delivers a log ~1.0 s after its block
  (wiki infra/feed.md, attempts:1029); ethereum blocks are ~12 s, so the bot scans at C-1+~2 s and
  its send can land in C. The bot does not count this class in EV (decision
  2026-11-13-next-block-feed: 1 block is a trial, not revenue); the trial measures whether the farm
  wins it.

## Capture windows and per-occurrence EV (review b69e96b8 fix 2; decision 2026-11-13-morpho3-stop-ev-net-of-gas table)

32 pinned-market ledger captures, blocks 26295008-26400631 (~15.7 d): 0-block 15 (12,313 USD
gross, race, not counted), 1-block 3 (4,083 USD gross, the whale among them; trial class, not
counted), >= 2-block 14 in 12 transactions (below, one row per tx; block 26373743 liquidates 3
positions in one tx and is ONE batched row). Gross = repaid x 4.384 pct (the measured 86 %-LLTV
liquidation bonus the protocol pays; same convention as attempts:1053). Gas = the capture tx's
gasUsed x effectiveGasPrice from its receipt (scratch/morpho-nextblock-fix/receipt_gas.json),
valued at ETH/USD 1,960 (this session's bot-measured UniV3 spot); the 2026-10-28/29 captures ran
at the 2.9-16.6 gwei base fee era. "Today" = the same seize priced at the CURRENT base fee
(~0.16 gwei, the mean effective price of the five 2026-11 captures 0.086-0.35 gwei).

| block | market | elig->taken blocks | gross USD | gas USD | net USD | net today | counted |
|---|---|---|---|---|---|---|---|
| 26301897 | WETH/USDC | 2-4 (accrual) | 1.953 | 7.71 | -5.76 | +1.91 | no: window < the 10 min poll and no feed trigger (WETH feed dormant) |
| 26301963 | WBTC/USDC | 128-256 | 0.069 | 13.07 | -13.00 | -0.06 | yes (BTC/USD AnswerUpdated trigger, >= 2 blocks) |
| 26302109 | WETH/USDC | 128-256 | 2.351 | 3.14 | -0.79 | +2.27 | yes (accrual class, window > 10 min poll) |
| 26302195 | WBTC/USDC | 512-1024 | 0.155 | 2.41 | -2.25 | -0.02 | yes (feed trigger) |
| 26302472 | WETH/USDC | 128-256 | 0.224 | 4.77 | -4.55 | +0.06 | yes (window > 10 min poll) |
| 26372995 | WETH/USDC | 8-16 (accrual) | 1.341 | 0.21 | +1.13 | +1.26 | no: 8-16 blocks = 1.5-3 min < the 10 min poll; the predecessor caught these with its 60 s scan (measured 100 s windows), this bot's safety poll cannot |
| 26372996 | WETH/USDC | 8-16 (accrual) | 0.999 | 1.74 | -0.75 | +0.92 | no: same as the row above |
| 26373222 | WETH/USDC | 128-256 | 0.172 | 0.19 | -0.01 | +0.09 | yes |
| 26373743 x3 | WETH/USDC | 128-256 | 0.040 | 0.07 | -0.03 | -0.09 | yes (one tx, three Liquidate events) |
| 26386155 | WETH/USDC | 256-512 | 0.105 | 0.15 | -0.05 | +0.01 | yes |
| 26391772 | WETH/USDC | 1024-2048 | 0.000 | 0.12 | -0.12 | -0.22 | yes |
| 26400631 | WBTC/USDC | 1024-2048 | 0.070 | 0.06 | +0.01 | -0.01 | yes |

Counted: 9 txs, gross 3.19 USD, measured gas 23.98 USD, measured net -20.79 USD over 15.7 d:
EVERY counted occurrence is net <= 0 at its actual tx gas, so counted EV = 0 USD/day (net <= 0
doesn't count). The predecessor's ~1.8 USD/day is NOT carried into this bot (reviewer item 2): its
counted EV rested on >= 8-block windows at the two 26372995/26372996 dust captures, whose measured
100 s/112 s windows are catchable by a 60 s scan but not by this bot's 10 min safety poll (and the
WETH/USD feed is dormant, so no feed wake puts them in reach). Trigger paths verified: the four
WBTC/USDC rows are BTC/USD AnswerUpdated-triggered (feed class, >= 2 blocks counts per decision
2026-11-13-next-block-feed); the WETH/USDC rows are interest-accrual crossings on the dormant-feed
market, counted only where the window exceeds the 10 min poll + inclusion. At today's base fee the
same nine occurrences net +2.04 USD = ~0.13 USD/day, still cents; under decision
2026-11-13-blocked-infra-feed-retriage item 3 the trial proceeds with zero counted EV (CU <= 50k
below). Read cost 0.02-0.03 USD/day (42k CU/day) stays below that ~0.13 USD/day and far below the
1M CU/day human line (decision 2026-11-12 item 6).

## Read cost (live Alchemy CU/day; review b69e96b8 fix 1 re-measure, run 0dad902a)

The running predecessor logs the numbers (logs/bot.jsonl): heartbeat rpc_cycle 3-4 at 609
candidates (1 header + ceil(calls/250) Multicall3 chunks), candidates_refreshed getlogs_calls per
refresh. Steady-state, after the deep backfill completes and with MAX_MARKETS capped at 4:

- feed: ~33 events/day x ~35 CU per delivered log row (886-byte single-log response, wiki) +
  subscription maintenance ~3-4 CU/min idle = ~6k CU/day.
- scan cycles: 144 timer cycles + ~33 feed-triggered cycles ~= 177 cycles x 5-6 reads (1 header +
  the Multicall3 chunks over the candidate set; the full 450k-block backfill finds ~610 pinned
  candidates - measured 112 + 319 over 320k blocks - plus a few hundred discovered ones, so
  calls stay under 1500 and chunks <= 6; heartbeats log rpc_cycle) ~= ~1000 reads/day x ~32 CU
  (the predecessor's measured average, 322,560 CU / 10,080 reads) ~= ~32k CU/day.
- refreshes: the cursor-resume window is ~150 blocks = ONE page per series; 48 refreshes x (2
  pinned + <= 2 discovered + 1 discovery series) = <= 240 getLogs/day x ~32 CU ~= 7.7k CU/day
  (MAX_MARKETS 8 -> 4: every tracked market adds one series to EVERY refresh page; at 8 markets the
  steady refresh cost ~14k CU/day).
- deep cold-start backfill (FIRST DAY ONLY, one-time): 6 batches x 10 pages x 3 series = ~180
  getLogs x ~32 CU ~= 5.8k CU. It was ~1,920 calls / ~61k CU before this fix: the batches scanned
  EVERY tracked market's candidates (discovery ballooned 2 -> 8 markets, 120 -> 360 calls/batch) at
  40 pages of 2000 blocks. Now the deep phase scans the PINNED markets' candidates only (the
  dormant-debtor class the backfill exists for; discovered markets are watch-only without pools)
  at 8000-block pages: the topic-filtered pinned series returned 231/286 logs and the all-
  liquidations series 23 logs over 8000 blocks at head (scratch/morpho-nextblock-fix/), far under
  the relay's log/size caps; the halving fallback still covers a denser era.
- steady total ~= 42k CU/day ~= 0.02 USD/day at 1M CU ~= 0.53 USD; first day ~= 48k incl. the
  backfill - under the 50k trial cap (decision 2026-11-13-blocked-infra-feed-retriage item 3). No
  feed subscription to a busy event (one idle filter, released 180 s after the last poll if the bot
  stops). First-day and steady-state CU are logged separately by the paper run's getlogs_calls /
  rpc_cycle rows; after the deepDone row the refresh logs stay <= ~5 calls.

## Bot behaviour

- Feed long-poll `GET http://127.0.0.1:8546/logs/ethereum?address=..&topic0=..&after=<cursor>&timeout=55`
  with the opaque cursor persisted in state/state.json (feedCursor); `gap`/reorg/error = re-read
  state through the relay once (the scan cycle itself) + backoff, never trust silence.
- Feed wake runs the next scan cycle immediately; the 10 min timer is only the safety poll; a scan
  is never overlapped (the wake during a running scan fires the next tick at its end).
- Paper mode simulates with the eth_call state-override carrying the constructor-patched fork
  runtime (executor-runtime.hex = eth_getCode of the fork-deployed executor 0xb464f731...);
  live mode sends the same calldata to EXECUTOR_ADDR through the signer. Send gate unchanged:
  only when expected gross > gas cap and above the 0.5 USD post-fee minProfit floor.
- Every opportunity, feed event and simulation result is logged machine-readably in logs/bot.jsonl.

## Fork proofs (re-run this session, lease 12 min taken and released)

Same deterministic fork state as the predecessor's accepted proofs (reset 26328589, deploy of the
shrunk MorphoLiquidator -> 0xb464f7314d55ec6a9a0cf6f7f6df17af8ed5b352):
SUCCESS 0xdb57c173c4cfa3feeec069058c796372627910b103be7e1804fdaeaeb79b0082 (gasUsed 332505, bot
wallet USDC 0 -> 3,711,168 = +3.711168 USDC PAID IN THE SAME TX, the executor left at ~0); REVERT on
the now-healthy position 0x9168710a37954c3f26533210ca1d1b1843f898c73f4e219132e6902b96d03b2b.
Rerun script for the reviewer: `fork lease ethereum 15` -> reset 26328589 -> fork deploy (artifact +
executor_args) -> `node scratch/morpho-eth2-proof.js liquidate WETHUSDC <execAddr>` -> `fork release`
(this session's raw output: scratch/morpho-nextblock/proof-liquidate.txt).
