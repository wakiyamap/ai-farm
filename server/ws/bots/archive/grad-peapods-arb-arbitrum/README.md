grad: graduated from `trial-peapods-arb-arbitrum` (decision `2026-11-24-graduate-and-builder-focus.md`). Same executor, same eight routes; the bot reacts in one relay round trip instead of eight. The trial stays live until this one is promoted; the human then stops it.

## Why this trial graduates

| condition | trial-peapods-arb-arbitrum |
|---|---|
| live 72 h or more | live since 2026-11-19 19:25Z, 84 h at 2026-11-23 07:40Z |
| net since promotion +1 USD or more | wallet 16.32 USD against 15 funded (`gate status`, 2026-11-23 07:4xZ); log: +0.002626 ETH net |
| 3 or more won sends | 5 won of 10 (`send_result: won`) |

## Mechanism (unchanged)

A Peapods pod (pTKN) is minted from its underlying by anyone with `bond()` and burnt back with `debond()`. Pods trade in Uniswap V2 / Camelot pairs. When a pod's pair price drifts from its underlying (mostly when PEAS moves on the Uniswap V3 PEAS/WETH pool 0x23d17764...), a round trip pays in one executor call: flash 0.004-0.010 WETH from the Balancer V2 Vault (fee 0), swap into the underlying, bond (or buy the pod and debond), cross the pair, unwind to WETH, repay; revert `NoProfit` unless the WETH balance grew by `minProfit`; the gain is paid to the bot wallet as native ETH. Routes and the incumbent takes they were copied from: the trial's README (`bots/live/trial-peapods-arb-arbitrum/README.md`).

## The trial's live record (`scratch/grad-peapods-arb-arbitrum/analyze.py`, `live-sends.json`)

84 h live: 29 gains seen, 19 gone before the gas estimate (`estimate_revert`), 10 sent.

| UTC | route | size WETH | result | gross ETH | gas ETH | blocks after winner |
|---|---|---|---|---|---|---|
| 11-19 19:44 | apump | 0.010 | won | 0.001542 | 0.000014 | - |
| 11-19 19:46 | parb_rev | 0.006 | won | 0.000540 | 0.000018 | - |
| 11-20 01:39 | parb_rev | 0.004 | won | 0.000205 | 0.000021 | - |
| 11-20 01:40 | apump | 0.004 | won | 0.000063 | 0.000013 | - |
| 11-20 16:35 | apump_rev | 0.006 | won | 0.000449 | 0.000014 | - |
| 11-21 16:01 | apump | 0.004 | lost | (0.000217) | 0.000011 | 0 |
| 11-22 01:23 | appeasusdc | 0.004 | lost | (0.000251) | 0.000029 | 3 |
| 11-22 02:43 | ppeas_usdc_rev | 0.006 | lost | (0.000261) | 0.000016 | 1 |
| 11-22 04:20 | parb_rev | 0.004 | lost | (0.000192) | 0.000021 | 0 |
| 11-22 08:11 | parb_rev | 0.002 | lost | (0.000077) | 0.000016 | 1 |

Won 5: +0.002719 ETH net. Lost 5: -0.000093 ETH. Net +0.002626 ETH (about 0.00075 ETH a day). All wins are from the first 21 h; the last five sends lost.

## Why the sends were lost, and what is changed

`scratch/grad-peapods-arb-arbitrum/origins.py` (`origins.json`) lists every Swap on the PEAS/WETH pool and the eight pod pairs before each send. The pattern is the same in all ten: an outside swap on the PEAS/WETH pool, then incumbent takes on one route after another 1-3 blocks later (0.25-0.75 s), and the trial's transaction 4-6 blocks after the outside swap. It won when a route was still open at that point, and lost 0, 0, 1, 1 and 3 blocks behind the winner. No lost send was a revert for another reason (all `NoProfit`: the gain was gone), and no fee was short: Arbitrum orders first come first served.

| | trial | grad |
|---|---|---|
| calls between the feed event and signing | probe, block, 4 size calls, estimate, guarded call: 8 in series | 3 probes (0.004 / 0.006 / 0.010 WETH), block and a gas estimate per route, all started at once: 1 round trip, 0.36 s at head (`selftest.py latest`) |
| second route paying in the same look | waits for the first send's receipt (up to 30 s) | signed at once; receipts are read on a side thread |
| minimum gap between two looks | 5 s | 0.3 s (takes cascade block after block) |
| wake-up | PEAS/WETH pool Swap, 60 s timer | the same pool Swap, V2 Swap on the eight pod pairs, 120 s timer |
| signer address | asked every look | asked once |
| new log fields | - | `timing` (probe_s, estimate_s, signed_s), `event_block`, `blocks_after_event` |

Not changed, on purpose: capital (15 USD, gas only) and size. The gain peaks at 0.004-0.010 WETH and reverts from 0.015 WETH up (fork sweep at block 525,710,104: parb_rev 0.000257 / 0.000412 / 0.000471 / 0.000330 ETH at 0.002 / 0.004 / 0.006 / 0.010; apump 0.000277 / 0.000428 / 0.000462 / 0.000208; the trial's ten live sweeps never chose its largest size), so a larger size or more capital earns nothing. No fee is bid: the winners paid 0.021-0.023 gwei priority on under 1m gas (under 0.000023 ETH, 5-10 pct of a typical gain) and it bought them no ordering.

What this does not fix: a take that lands 1 block after the outside swap. If the grad still loses 0-1 blocks behind, the remaining gap is the feed and the sequencer, and the lead closes as `blocked_infra`.

## Competition (trial README, 7 days to block 525,545,222)

418 takes by three executors, each driven by one EOA: 0x9934b3b1 196, 0xda77151b 203, 0x429e114b 19; bursty (304 in one day, 9-47 a day otherwise). Winners of the trial's lost sends: txs 0xa219018c..., 0x109c51bf..., 0x0a66eb95..., 0xb3c48b95..., 0x14674360... (`live-sends.json`).

## Windows

Read from `origins.json` (blocks are 0.25 s; "outside swap" = the last PEAS/WETH swap that is not part of a take):

| lost send (block) | outside swap -> first incumbent take | outside swap -> the take that beat us | outside swap -> our tx |
|---|---|---|---|
| 526,281,369 | 2 | 3 | 3 |
| 526,384,748 | 1 | 1 | 4 |
| 526,399,448 | 1 | 3 | 4 |
| 526,418,341 | 2 | 4 | 4 |
| 526,462,372 | 2 | 3 | 4 |

The five wins landed 4-5 blocks after the outside swap. So the first incumbent take comes 1-2 blocks (0.25-0.5 s, minimum 0.25 s) after the swap and is out of reach; the take that beat the trial came at a median of 3 blocks (0.75 s), and four of the five were at 3-4 blocks, which a bot 2 blocks faster reaches. This is inside the farm's 3 s reaction class, so by the race rule it is not counted revenue; the expected value in the manifest rests on the trial's live record, as the graduation decision allows.

## How it sends

1. A feed event (or the timer) starts `check()`. Event: `probe()` at three sizes, the base fee and `eth_estimateGas` of `run()` at 0.004 WETH for each of the eight routes go out together.
2. For each route with a gain, best size first: gas limit = estimate x 1.20 + 600,000 (refused above 3.2m), `maxFeePerGas` = base fee x 1.05 + 1 wei (refused above 0.1 gwei), cap = limit x fee (refused at 0.90 USD at a 4,000 USD/ETH reference; typical 0.05-0.10 USD). Signed only if the gain is above the cap, with `minProfit = cap + 1`.
3. Paper mode logs `opportunity` and simulates the signed call (`paper_sim`). Live mode signs through the signer and logs `send`, then `send_result` (won / lost, gas, winner's block and tx, blocks after the event).

A lost attempt costs gas only: 0.000011-0.000029 ETH in the trial.

## Fork proof

`python3 scratch/grad-peapods-arb-arbitrum/proof.py 525710104 proof-525710104.json` (the trial's proof script on the same artifact; leases and releases the Arbitrum fork). Run 2026-11-23 at the parent of the trial's first live win: non-owner revert `0x21a08908...`, `NoProfit` guard revert `0x74d1d875...`, successes parb_rev `0xe11c9a5c...` +0.000374766 ETH net and apump `0x12e4bcce...` +0.000412707 ETH net, executor clean after each, repeats revert. `python3 scratch/grad-peapods-arb-arbitrum/selftest.py 525710104` replays the bot's own `check()` at that block (three routes, each `paper_sim` success).

## Reads

Timer 720 x 26 CU = 18,720 CU/day. An event look is 258 CU (3 x 26 + 20 + 8 x 20); at 300-500 swaps a day that is 77,000-129,000 CU/day. Code cap 250,000 relay CU/day = 0.13 USD at 0.53 USD per million CU; at the cap the bot sleeps to 00:00 UTC. Feed: two filters on arbitrum (the PEAS/WETH one is the trial's filter), metered by the feed. No per-block polling.

## Logs and closing

`logs/bot.jsonl`: `start`, `check`, `opportunity`, `opportunity_skip`, `paper_sim`, `send`, `send_result`, `signer_reject`, `feed_error`, `read_budget`, `loop_error`. After 7 days live: sends, wins, net ETH and `blocks_after_event` against the trial's table above go into an `attempts` row.
