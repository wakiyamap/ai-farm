grad: ERN below-par redemption on Ethos Reserve (OP Mainnet). Graduated from the live trial `trial-ethos-redeem-optimism` (decision 2026-11-24-graduate-and-builder-focus). Same executor bytecode, same fee, same 5 USD of native gas. Changes: larger flash-loan sizes when they pay, follow-up takes right after a win, and fewer reads (10 min safety poll instead of the trial's 120 s timer).

Revision 2026-11-24 03:47Z (run ff15b841, answering review dc5b4d5c): all trial amounts below are what the wallet received (USDC `Transfer` logs in the receipts), no longer the pre-send simulation; feed gap / error now re-reads state at once; read cost measured and cut. See "What changed in this revision" at the end.

## Mechanism (unchanged)

ERN (0xc5b001dc...) trades below 1 USD on the Velodrome ERN/USDC pool 0x605cce50.... Ethos Reserve (a Liquity fork) lets anyone redeem ERN at par for WETH through `TroveManager.redeemCollateral` (0x75c72f45..., no role). One executor call: Balancer V2 flash loan of USDC (0 fee) -> buy ERN on the pool -> `redeemCollateral` (NICR hint computed on-chain) -> sell the WETH on Uniswap V3 0.05% -> repay -> revert `NoProfit` unless the USDC balance grew by `minProfit` -> gain to the bot wallet as USDC.

## 1. Live record of the trial (realized, from receipts)

Source: every `send_result` hash of `bots/live/trial-ethos-redeem-optimism/logs/bot.jsonl`, its receipt, and the sum of USDC `Transfer` logs to the trial wallet 0x86e85246...: `scratch/grad-ethos-redeem-optimism/realized.py` -> `realized.json` (the first 43 receipts are the reviewer's `review-receipts-dc5b.json`, the 15 later ones were fetched by this script). Promoted 2026-11-19 17:41Z, first send 18:20:23Z (block 159,756,823); numbers as of the log's last row, 2026-11-24 03:39Z: 106.0 h since promotion. Gas in USD at 1,717.18 USD/ETH.

| | |
|---|---|
| sends | 58 |
| won | 46 (79%) |
| USDC received by the wallet in the 46 wins | **2.298649** |
| (the log's pre-send simulation for the same 46) | (3.053503: not proceeds) |
| gas of all 58 sends (L2 + L1) | 0.0502 USD (0.0138 USD of it on the 12 lost sends) |
| realized net | **+2.248 USD** in 106.0 h (0.51 USD/day) |
| net by the gate (wallet now minus funded, `grad-candidates.py` 03:45Z) | +2.25 USD |

Why the log overstated: `send_result.gross_usdc` was the simulation made before the send; the state at inclusion was 1-3 s later. 23 of 46 wins differ from it by more than 10 micro-USDC (both ways: 0x7a14b2f8... simulated 5,159, received 10,269; 0x60e08962... simulated 23,183, received 5,054). The grad logs `realized_usdc` from the receipt in every `send_result` (bot.py `send_live`).

One take is 89% of the received USDC: 0xa9aff679... in block 159,938,192 (2026-11-23 **23:06:01Z**, block timestamp), 40 USDC, the trial's largest size. Simulated +2.813520, **received +2.043943**: the rival's take landed one block earlier, and 2.043943 is exactly what the fork gives for 40 USDC on the state after it (section 4). The other 45 wins total 0.254706 USDC (0.0004-0.045 each, 21 of them above 0.004).

By trigger: Sync-triggered sends 37 (26 won, 2.2445 USDC, 0.2006 without the big one); timer-triggered sends 21 (20 won, 0.0542 USDC). The trial's 120 s timer made 1,897 checks for those 0.054 USDC.

The 11-23 event, block by block (`event.py`, `rivals.json`; times are block timestamps, 2 s blocks back from 159,938,192 = 23:06:01Z): a 625 ERN sale into the pool in block 159,938,189 (23:05:55Z, tx 0x70cf9ceb...). Rival 0x6ce08b79 took 5.22 USDC in block 159,938,191 (+4 s, index 2). The trial took 2.04 in 159,938,192 (+6 s, index 6) and then sat in its 60 s cooldown. The rival took six more: 2.54 (block ...194, +10 s), 1.14 (...197), 0.38 (...200), 0.19 (...203), 0.08 (...206), 0.03 (...210, +42 s): 4.35 USDC taken 10-42 s after the event started, with 100-ish USDC per take (pool USDC reserve rises by 75-100 per take).

Race rule (R = 3 s): the farm's earliest block for this event is 159,938,191. The rival's first take is in it; the trial's take is 2 s after it (may be tried, **not counted**). The rival's six later takes are 6 s or more after it: counted class, but see "Expected value" for what of them a larger first take leaves.

## 2. Fee share of the winners

OP Mainnet: priority fee does not buy an earlier position (the grad rule for OP Stack: no fee increase). The table is here to show that nobody pays for position either. Shares are of the USDC actually received (`feestats.py` -> `feestats.json`).

| who | takes in the window | priority fee | priority x gas used / received | all gas (L2 + L1) / received |
|---|---|---|---|---|
| trial (ours) | 46 won | 2,000,000 wei, capped at 15% of the simulated gross | min 0.1%, median 9.8%, p90 11.1%, max 49.9% | min 0.1%, median 13.6%, p90 24.8%, max 58.3% |
| rival 0x6ce08b79 | 13 (to 11-23 23:47Z) | 1,000,000 wei every time | min 0.03%, median 1.6%, max 5.9% | min 0.03%, median 1.7%, max 7.0% |

(rival window blocks 159,755,600-159,939,421, `rivals.py` -> `rivals.json`, not re-run in this revision. Two more Redemption events came from 0xcadcb387 with no USDC to the sender: a holder's own redemption, not a take.) The 49.9% maximum is the win that received 5,054 after a simulation of 23,183: the cap is a share of the simulated gross, so a take that shrinks before inclusion pays a larger share; in USD it was 0.0025. The rival's transaction index was 1-137; the trial's lost sends were index 10-162. The grad keeps the trial's fee exactly: 2,000,000 wei per gas, never above 15% of the simulated gross (`TIP_WEI`, `BID_SHARE`).

## 3. Why the trial lost 12 sends, and what changes

All 12 reverted inside the executor at a cost of 0.00006-0.0033 USD each (0.0138 USD in total). Revert data of the first 10 from `debug_traceTransaction` (`trial-sends.json`); the last two (11-24) were not traced, they are 5 USDC sends of the same shape.

| block | size | simulated gross (micro-USDC) | revert | cause |
|---|---|---|---|---|
| 159,760,201 | 5 | 1,138 | NoProfit(346, 349) | gain shrank by 3 micro-USDC under the minimum between simulation and inclusion |
| 159,770,507 | 15 | 18,809 | USDC "transfer amount exceeds balance" at repay | state moved, no redemption by anyone within 300 blocks (pool or oracle price) |
| 159,772,435 | 5 | 1,631 | same | same |
| 159,774,490 | 5 | 337 | same | same |
| 159,794,633 | 10 | 11,001 | same | rival's take 2 blocks earlier (159,794,631) |
| 159,797,344 | 10 | 8,049 | same | state moved, no redemption nearby |
| 159,821,539 | 10 | 6,845 | same | rival's take 2 blocks earlier (159,821,537) |
| 159,822,338 | 10 | 6,277 | same | state moved (last redemption was our own, 118 blocks earlier) |
| 159,834,711 | 10 | 34,730 | same | rival's take in the same block (index 99, ours 162) |
| 159,902,623 | 40 | 106,860 | same | state moved, no redemption nearby |
| 159,943,486 | 5 | 1,490 | reverted (not traced) | last redemption 57 blocks earlier: state moved |
| 159,945,394 | 5 | 407 | reverted (not traced) | no redemption within 300 blocks: state moved |

"transfer amount exceeds balance" is the executor failing to repay the flash loan because the round trip no longer covers it: the same meaning as `NoProfit`, reached one step earlier. Three losses are to the rival by 0-2 blocks, nine are the price moving in the 1-3 s between simulation and inclusion. Simulation to signer took 0.72-1.33 s. None of this is fixable by fee on OP Mainnet, and the whole cost was 0.014 USD against 2.30 USDC received, so the grad leaves the send path as it is. What it changes is where the trial left money or spent reads:

1. **Size** (section 4): the sweep goes up 5, 10, 15, 20, 25, 30, 40, 60, 80, 120, 160, 240, 320, 400 USDC and stops at the first size that does not improve.
2. **Follow-up takes**: after a won send the bot checks again at once (up to 8 times in a row) instead of waiting 60 s. After a lost send it waits 10 s (was 60 s).
3. **Reads**: 10 min safety poll instead of the 120 s timer (the timer's 1,897 checks cost 148k CU = 0.078 USD for 0.054 USDC of wins); `sortedTroves()` read once; the size sweep stops at the first size that does not improve (an ordinary 5 USDC case costs one more `eth_call`, not six).

## 4. Size: fork proof at past winning blocks

`scratch/grad-ethos-redeem-optimism/size.py` -> `size-result.json` (one optimism fork lease; reset to the parent block, deploy the unchanged artifact, sweep; at the first block real fork transactions from one snapshot). Reproduced by the reviewer (`review-size-dc5b4d5c.json`).

| parent block (trial send) | 5 | 10 | 20 | 40 (1x) | 80 (2x) | 120 | 160 | 200 (5x) | 300+ |
|---|---|---|---|---|---|---|---|---|---|
| 159,938,191 (the 40 USDC win) | 0.309 | 0.603 | 1.144 | 2.044 | 3.161 | **3.438** | 2.956 | 1.784 | revert |
| 159,902,622 (40 USDC, lost) | 0.025 | 0.046 | 0.075 | **0.085** (30: 0.088) | revert | | | | |
| 159,830,992 (20 USDC win) | 0.019 | 0.033 | **0.048** | 0.020 | revert | | | | |
| 159,822,219 (15 USDC win) | 0.007 | **0.009** | revert | | | | | | |
| 159,800,946 (5 USDC win) | 0.006 | **0.007** | revert | | | | | | |

(gross in USDC; flash-loaned, so the bot's capital does not change.) Fork transactions at parent 159,938,191, each from the same snapshot, owner USDC delta: 40 USDC 0x23759e5a... +2.043943 (equal to what the trial's wallet received in the real block 159,938,192); 80 USDC 0xa38e1b17... +3.160746; 200 USDC 0x097b7ee8... +1.783846; 120 USDC 0x7763db30... +3.438282 (809,761 gas, executor left with 0 USDC / ERN / WETH).

Reading: size pays only in a deep-discount event (1 in 106 h so far): there, 3x the size gives 1.7x the gross (+1.39 USDC on that one take), and 5x gives less than 1x. In the ordinary cases the best size is 10-30 USDC and the trial already had it. The pool holds 1,300-1,900 USDC, so nothing above about 160 USDC has paid. `capital_usd` stays 5 (native gas only).

## Expected value

All from the trial's realized record (section 1), not a forecast.

| class | what | realized | per day (106.0 h) |
|---|---|---|---|
| all | 46 wins, all 58 sends' gas | +2.248 USD | 0.51 USD |
| not counted (tried) | the first take of the 11-23 event, 2 s after the farm's earliest block | 2.043943 USDC | |
| **counted** | the other 45 wins, 0.254706 USDC, minus the gas of all 58 sends, 0.0502 USD | **+0.2045 USD** | **0.046 USD** |
| read cost of the grad (next section) | 39.5k CU/day at the trial's average event rate | | 0.021 USD |
| **counted net of reads** | | | **about +0.025 USD** |

Conditional, stated separately, not in the counted line:

- **Larger first take in a deep-discount event** (not counted: it is the 2 s class): on the fork at the state of the trial's big win, 120 USDC takes 3.438 where 40 took 2.044, +1.39 USDC per such event. One such event in 106 h.
- **Follow-up takes after it** (counted class, but fork only, no live capture): after a 120 USDC first take the fork leaves three more 5 USDC takes worth 0.022057 + 0.011956 + 0.001990 = **0.036003 USDC**, then it reverts (reviewer's replay `review-followup-dc5b.py`). The 4.35 USDC the rival took 10-42 s after the start on 11-23 existed because both first takes were small; with the grad's own 120 USDC first take most of it is in that take, not after it. At one event per 106 h this is 0.008 USD/day: it does not carry the bot.
- The trial is still winning at the old state of the market: 11-24 00:00-03:39Z, 16 sends, 14 won, 0.051634 USDC received, gas 0.0060 USD (0.30 USD/day rate over those 3.7 h; a busy stretch, 1,186 Sync/day rate against the 397/day average).

So the honest size of this bot: about 0.05 USD/day of small counted takes against 0.02 USD/day of reads, plus a deep-discount event about once in 4-5 days where the grad's size sweep is worth +1.4 USDC over the trial (tried, not counted).

Windows of the ordinary cases (measured for the trial over the 31 incumbent takes of 11-11..11-18, `scratch/trial-ethos-redeem-optimism/windows.json`): at this bot's threshold, median 30 s (15 blocks) and minimum 2 s (1 block) from takeable to taken; 17 of 31 were takeable 30 s or more before the incumbent took them, 10 at least 3 min, 3 at least 10 min. The incumbent waits for about 0.02 USDC per take (calldata minimum 22,085 micro-USDC); this bot takes from the gas cap up (about 0.004 USD).

## Bot

- Waits on the feed for `Sync(uint256,uint256)` on the pool 0x605cce50... (397 a day on average, measured) with a 600 s safety poll through the relay.
- **Feed recovery** (bot.py `main`): `gap: true` -> re-read state at once, with no spacing; HTTP 429 / 503 / connection error / timeout of the feed call -> re-read state at once, then wait 30 / 60 / 120 s (1st / 2nd / later error in a row) and resume with the same cursor. A Sync that arrives within 10 s of the last check is not dropped: the next feed call is shortened so the check runs when the 10 s end. Scripted test of the real `main()` loop: `scratch/grad-ethos-redeem-optimism/feedtest.py` -> `feedtest-result.json` (PASS: gap 0.5 s after a check -> re-read after 0 s; 429, 503, URLError, RemoteDisconnected, TimeoutError -> re-read after 0 s, sleeps 30, 60, 120, 120, 120; Sync 2 s after a check -> checked 9 s later).
- Check: lowest WETH trove (`sortedTroves.getLast`), a 5 USDC probe simulation, then larger sizes while the gain grows.
- Sends only when gross > signed gas cap (`gasLimit x maxFee + 1e11 wei` L1 allowance), `minProfit = cap + 1`, after simulating the exact guarded call at the signed gas limit. Signed cap refused at 0.90 USD; typical 0.004 USD.
- Logs: `check`, `opportunity` (with the size sweep), `opportunity_skip`, `paper_sim`, `send`, `send_result` (won / lost, gas used, winner block, `realized_usdc` from the receipt, `sim_gross_usdc`) in `logs/bot.jsonl`.
- Self-test after this revision's changes (`scratch/grad-ethos-redeem-optimism/selftest.py`, the bot's own `check_loop` at fixed blocks through the relay, 2026-11-24 03:44Z): 159,938,191 -> sweep 5..160, 120 USDC, gross 3,438,282, paper_sim success; 159,902,622 -> 30 USDC, gross 88,017; 159,938,400 -> nothing_to_take.
- Paper note: while the trial is live it takes the same opportunities first, so paper rows after the trial's send show `estimate_revert` / `simulate_revert` (review dc5b: explained same-opportunity miss).

## Read cost (measured, `scratch/grad-ethos-redeem-optimism/cost.py` -> `cost.json`, 2026-11-24 03:45Z)

Feed, measured: the pool Sync filter's `cu_today` in `/health` was 5,043 CU at 03:45Z (3.76 h of 11-24) while the pool emitted 186 Sync logs in the same hours (`eth_getLogs`): 3.5 CU/min maintenance + **22.9 CU per Sync**. The pool emitted 1,743 Sync in the trial's 105.4 h = 397/day, so the feed costs **14.1k CU/day** on average (32.2k/day at this night's 1,186 Sync/day rate). One filter, shared with the trial while both run (2 waiters on one subscription).

Relay, from the trial's own counts per day (248 Sync-triggered checks, 19.8 opportunities, 13.0 sends) at the grad's per-item cost:

| item | CU each | per day | CU/day |
|---|---|---|---|
| Sync-triggered check (`getLast` + probe) | 52 | 248 | 12.9k |
| safety poll check (only if no check for 600 s) | 52 | at most 144 | 7.5k |
| opportunity (1 more size, `fetchPrice`, block, `estimateGas`, final simulation) | 118 | 19.8 | 2.3k |
| send (receipt polls, `eth_getLogs`, follow-up check) | 207 | 13.0 | 2.7k |
| **relay total** | | | **25.4k** |

**Total 39.5k CU/day = 0.021 USD/day** at 0.53 USD per million CU (the previous revision: 72-102k CU/day by the reviewer's count). At this night's event rate (3x the average) the same model gives 93k CU/day = 0.049 USD/day, during hours in which the trial realized 0.30 USD/day. Code cap 60,000 relay CU/day (`RELAY_CU_CAP`), every read inside the loop's handlers; at the cap the bot sleeps and logs `read_budget`. A feed outage costs at most 720 re-reads a day (120 s backoff) = 37k CU, inside the cap. While the trial is still live both bots read until the human stops the trial.

## Evidence

`scratch/grad-ethos-redeem-optimism/`: `realized.py` + `realized.json` (receipts, realized USDC, trigger of each send), `feestats.py` + `feestats.json` (fee shares of received USDC), `cost.py` + `cost.json` (feed and relay cost), `feedtest.py` + `feedtest-result.json` (feed recovery), `analyze.py` + `trial-sends.json` (revert reasons of the first 10 lost sends; its gross column is the simulation, superseded by `realized.json`), `rivals.py` + `rivals.json` (rival fee table), `event.py` (11-23 timeline), `size.py` + `size-result.json` (fork), `selftest.py` + `selftest-*.jsonl`, the reviewer's `review-receipts-dc5b.json`, `review-size-dc5b4d5c.json`, `review-followup-dc5b.py`. Executor source and the trial's original proof: `scratch/trial-ethos-redeem-optimism/` (`proof.py`, `proof-result.json`).

## What changed in this revision (review dc5b4d5c, points 1-3)

1. Feed recovery: `gap` and every feed error re-read state immediately (was: skipped within 10 s of a check; after an error only when the 120 s timer was due). Tested with `feedtest.py`. The recovery reads are in the CU table (outage worst case 37k CU/day, inside the 60k cap).
2. Revenue: every trial figure recomputed from receipts (2.298649 USDC received in 46 wins, not the simulated 3.05); fee shares recomputed on received USDC; the big win's time corrected to 23:06:01Z (block 159,938,192) and the event start to 23:05:55Z; the bot now logs `realized_usdc`.
3. Read cost: feed usage measured (22.9 CU per Sync, 14.1k CU/day), relay reads cut from 78 to 52 CU per check, timer 120 s -> 600 s, lazy size sweep: 39.5k CU/day = 0.021 USD/day against 0.046 USD/day counted realized net. Follow-up EV stated separately as conditional (0.036 USDC per deep-discount event, fork only).

Executor bytecode, manifest caps, fee and send path are unchanged; `executor-runtime.hex` is unchanged (no source change).
