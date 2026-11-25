# aave-watcher2-ethereum

Revival of the archived aave-watcher-ethereum (same executor, same watcher) as a
poll bot for the reopened lead 17 (decision 2026-11-13-blocked-infra-feed-retriage
item 2 reopened it: >=2-block windows with net >> feed CU).

## What it waits on

- Poll: 8 s cycle, round-robin 200-user Multicall3 getUserAccountData chunks over
  the discovered candidate universe (LiquidationCall/Borrow/Repay discovery),
  HF < 1.005 band -> simulate the executor -> send when live.
- Feed option (for the reviewer's feed checklist): the trigger for the slow
  interest-bleed class is the Chainlink price update, NOT a busy event; the
  per-market aggregators are not pinned yet (the pinned wrapper emits no
  AnswerUpdated logs — measured in lead 14's feed finding). Poll cadence is the
  safe path until the aggregator is pinned; the fresh recount measured the
  countable windows at 24-72 s (2-6 blocks), which an 8 s poll catches but a
  pinned feed could shorten further.
- Safety poll: the 8 s cycle is itself far above the 5-10 min feed-poll floor; on
  gap/429/503 the bot re-reads state through the relay (bot.js catch paths).

## Per-occurrence EV table — fresh 30 d recount (decisions 2026-11-13-morpho3 item 2 + 2026-11-13-aave-watcher2-recount)

Same 14 farm-band (10-1200 USD cover) supported-pair captures, ledger window
blocks 26284068-26402919 (~16.1 d), re-measured 2026-11-13 with the padded
`getUserAccountData` probe (the 11-13 "eth_call relay incident" was OUR unpadded
address in the probe calldata — the relay was fine; lead 17 CORRECTION). Bonus
is the value read from `getConfiguration(collateral)` at the capture's parent
block: 10500 bps = 5 pct (one USDC->WETH row 10450), NOT the 10 pct the earlier
table assumed (review 1091 blocker 5). Gas column = the incumbent capture tx.
Full JSON: scratch/aave-eth-revive/recount2_out.json.

| block | pair | cover USD | gross USD (5 pct) | incumbent gas USD | net USD | window blocks | counted? |
|---|---|---|---|---|---|---|---|
| 26384825 | WETH->USDC | 1113.63 | 55.68 | 1.18 | 54.50 | 0 | same-block crossing (excluded) |
| 26372987 | WETH->USDC | 1022.38 | 51.12 | 1.16 | 49.96 | 6 | **counted** |
| 26385472 | WETH->USDC | 1018.73 | 50.94 | 13.39 | 37.55 | 0 | same-block crossing (excluded) |
| 26300887 | WETH->USDC | 824.35 | 41.22 | 79.33 | -38.11 | 0 | same-block crossing (excluded) |
| 26375762 | WETH->USDC | 582.89 | 29.14 | 0.18 | 28.96 | 1 | 1-block window (feed-only try, not counted) |
| 26385472 | WETH->USDC | 298.44 | 14.92 | 13.39 | 1.53 | 0 | same-block crossing (excluded) |
| 26351313 | WETH->USDC | 100.09 | 5.00 | 0.28 | 4.72 | 0 | same-block crossing (excluded) |
| 26301942 | WETH->USDC | 74.31 | 3.72 | 14.52 | -10.80 | 2 | window >=2 but net <= 0 |
| 26342235 | USDC->WETH | 63.32 | 2.85 | 5.11 | -2.26 | 4 | window >=2 but net <= 0 |
| 26399074 | WETH->USDC | 50.38 | 2.52 | 0.29 | 2.23 | 3 | **counted** |
| 26384827 | WETH->USDC | 44.43 | 2.22 | 0.39 | 1.83 | 2 | **counted** |
| 26372987 | WETH->USDC | 36.10 | 1.80 | 1.16 | 0.64 | 6 | **counted** |
| 26351314 | WETH->USDC | 33.06 | 1.65 | 0.26 | 1.39 | 1 | 1-block window (feed-only try, not counted) |
| 26372987 | WETH->USDC | 18.77 | 0.94 | 1.16 | -0.22 | 6 | window >=2 but net <= 0 |

Countable EV (decision 2026-11-13: windows >=2 blocks, net > 0 after the
incumbent gas column): **4 captures, 54.66 USD over 16.1 d = 3.4 USD/day**
(the 26372987 cascade rows share one incumbent gas figure — that column
slightly overcounts those rows). Before filtering: gross 263.72 USD, net
131.92 USD = 16.4 / 8.2 USD/day. Our own send pays below the incumbent column
(no priority race needed at >=2-block windows; the fresh USD check refuses
above 20 USD).

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

~30 relay reads/min worst case (8 s cycle, one Multicall3 aggregate per chunk of
200 users; 200-user chunks are ~15 CU each at Alchemy) ~= 0.4-0.9M CU/day
~= 0.2-0.5 USD/day at 1M CU ~= 0.53 USD — well below the EV/day above.

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
