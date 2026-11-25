# sherlock-arb-ethereum

Takes the public `arbRestake(id)` reward of the Sherlock V2 staking pool on ethereum
(`0x0865a889183039689034dA55c1Fd12aF5083eabF`, verified `Sherlock.sol`; KB lead 391, attempts:3605 / 3608).

## Mechanism

A staking position is an NFT id holding USDC with a `lockupEnd(id)`. If its owner neither redeems nor restakes it within
2 weeks after the lockup ended, anyone may call `arbRestake(id)`: the position is locked for another 26 weeks and the
caller is paid USDC out of it. The reward is 0 at `lockupEnd + 2 weeks` and grows linearly to 20 % of the position over
the next 7 days (`_calcSharesForArbRestake`). So every start time is known weeks ahead, and waiting longer pays more,
until somebody else takes it.

## What the bot does

1. Once a day: `lockupEnd(id)` for every id up to the highest live id + 150 (about 865 `eth_call`).
2. Sleeps until a position is `LAG_S` = 6 h into its ramp (no polling in between; times are precomputed).
3. Reads `viewRewardForArbRestake(id)` for the ready ids, keeps those whose reward covers their share of the gas cap,
   simulates `SherlockArb.run(pool, USDC, ids, minProfit, deadlineBlock)` with the exact bytes and estimates gas.
4. Live: sends when reward - gas cap >= 0.02 USD, `minProfit = max(95 % of the simulation, gas cap)`, deadline head + 3.
   Paper: logs `opportunity` + `paper_sim` once per occurrence, and `position_left_ramp` when somebody else restakes it.
5. A position whose reward is still under gas is looked at again every 30 min.

Private send (`send_route: private`): the call is simple to copy from the public mempool (anyone may call
`arbRestake` directly), and a send that would revert because somebody restaked first then costs nothing.

## Expected value, per occurrence (added 2026-11-22 for review 5d70740b)

**Conclusion first: the counted-class EV is 0.09 USD/day over the last 30 days and 0.15 USD/day over the last 361 days,
net of gas. That is below 1 USD/day.** The earlier "0.3 to 2 USD/day" was the incumbents' realized gross, not what this
bot's rule would have earned; it is withdrawn. The reviewer should judge the bot on the numbers below.

Source: `scratch/sherlock-arb-ethereum/occurrences.py <days> [prefix]` (one row per `ArbRestaked` log; re-runnable, about
20 s and 350 relay calls for 30 days), outputs `occurrences.json` / `.md` / `-summary.json` (30 d, blocks 26,252,924 -
26,468,924) and `y361-occurrences.*` (361 d, blocks 23,869,727 - 26,468,927). Run at 2026-11-22T06:44Z.

How each column is computed:

- **ramp start** = `lockupEnd(id)` read at the parent block of the take + 2 weeks. **take** = the incumbent's block.
  The linear model (0.2 x position x elapsed / 7 d) reproduces every logged reward within 0.0001 USDC (402 of 402).
- **incumbent**: reward = `ArbRestaked` data word 0; gas share = the transaction's `gasUsed x effectiveGasPrice x ETH/USD`
  **split equally over the ArbRestaked logs of that transaction**; net = reward - share.
- **bot** (bot.py rules replayed, one id per send, i.e. no batching, which is the expensive case): first check at ramp
  start + 6 h (`LAG_S`), then every 30 min (`RETRY_S`); it sends at the first check where reward - gas cap >= 0.02 USD
  (`MIN_NET_USD`), gas cap = 335,120 gas (estimate in the paper log) x 1.3 x maxFee x ETH/USD, maxFee = min(3 gwei,
  1.5 x base fee + 0.1 gwei). "bot threshold" is that reward. Base fee and ETH/USD (Uniswap V3 USDC/WETH 0.05 % `slot0`,
  the bot's own source) are those of the incumbent's take block, the one block read per occurrence (a stated proxy).
  **bot gross** = the reward at the bot's send time (not the incumbent's later, larger reward); **bot gas** = 314,487 gas
  (fork proof) x (base fee + 0.1 gwei) x ETH/USD: the bot's own single-id send, not a share of anybody's batch.
- **window s** = incumbent take time - the bot's send time (the first moment the bot's own condition is true).
  **class**: `counted` when the window is at least 24 s (the farm's earliest block is at most R = 12 s after the takeable
  time, and the take came at least R after that); `not_takeable` when the incumbent took the position before the bot's
  condition was ever true (window negative or the reward never reaches the threshold): gross 0, no send, nothing counted.
  No occurrence fell in between (`same_window` = 0).

### Last 30 days (71 occurrences in 7 transactions, 5 senders)

| | n | gross USDC | gas USD | net USD |
|---|---|---|---|---|
| incumbents, as taken | 71 | 13.99 | 2.68 | 11.31 |
| bot, counted class (all 22 have positive net) | 22 | 5.61 | 2.87 | **2.73 = 0.091 USD/day** |
| bot, not takeable | 49 | 0 | 0 | 0 |

Counted windows: minimum 564 s (47 blocks), median 41,424 s (3,452 blocks). Dropping the one counted row whose window
is under one 30 min check interval (sensitive to the check phase): 21 rows, net 2.58 USD = 0.086 USD/day.

| id | position USDC | ramp start (UTC) | take (UTC) | take block | tx (ids in tx) | h from ramp start | incumbent reward | incumbent gas share | incumbent net | bot threshold | bot send at (h) | window s | class | bot gross | bot gas | bot net |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 703 | 4843.74 | 11-08 00:21:59 | 11-08 00:33:35 | 26366591 | 0x749de1ab… (1) | 0.2 | 1.1148 | 0.0489 | 1.0659 | 0.170 | 6.0 | -20904 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 314 | 13.03 | 11-15 03:51:35 | 11-16 09:18:23 | 26426643 | 0xaebfdce1… (7) | 29.4 | 0.4568 | 0.0462 | 0.4106 | 0.277 | 18.0 | 41208 | counted | 0.2793 | 0.1423 | 0.1370 |
| 322 | 10.82 | 11-15 07:38:11 | 11-16 09:18:23 | 26426643 | 0xaebfdce1… (7) | 25.7 | 0.3308 | 0.0462 | 0.2846 | 0.277 | 21.5 | 15012 | counted | 0.2771 | 0.1423 | 0.1348 |
| 430 | 10.3 | 11-15 08:44:11 | 11-16 09:18:23 | 26426643 | 0xaebfdce1… (7) | 24.6 | 0.3012 | 0.0462 | 0.2550 | 0.277 | 23.0 | 5652 | counted | 0.2819 | 0.1423 | 0.1397 |
| 556 | 13.08 | 11-15 03:47:59 | 11-16 09:18:23 | 26426643 | 0xaebfdce1… (7) | 29.5 | 0.4593 | 0.0462 | 0.4131 | 0.277 | 18.0 | 41424 | counted | 0.2802 | 0.1423 | 0.1379 |
| 570 | 12.56 | 11-15 04:33:11 | 11-16 09:18:23 | 26426643 | 0xaebfdce1… (7) | 28.8 | 0.4299 | 0.0462 | 0.3837 | 0.277 | 18.5 | 36912 | counted | 0.2766 | 0.1423 | 0.1343 |
| 571 | 12.17 | 11-15 05:10:35 | 11-16 09:18:23 | 26426643 | 0xaebfdce1… (7) | 28.1 | 0.4074 | 0.0462 | 0.3612 | 0.277 | 19.5 | 31068 | counted | 0.2824 | 0.1423 | 0.1401 |
| 699 | 11.07 | 11-15 07:07:59 | 11-16 09:18:23 | 26426643 | 0xaebfdce1… (7) | 26.2 | 0.3448 | 0.0462 | 0.2986 | 0.277 | 21.0 | 18624 | counted | 0.2767 | 0.1423 | 0.1344 |
| 61 | 9.78 | 11-15 09:57:59 | 11-16 12:37:23 | 26427637 | 0x60923300… (3) | 26.7 | 0.3102 | 0.0693 | 0.2409 | 0.303 | 26.5 | 564 | counted | 0.3084 | 0.1549 | 0.1535 |
| 278 | 10.25 | 11-15 08:51:59 | 11-16 12:37:23 | 26427637 | 0x60923300… (3) | 27.8 | 0.3388 | 0.0693 | 0.2695 | 0.303 | 25.0 | 9924 | counted | 0.3052 | 0.1549 | 0.1503 |
| 388 | 10.26 | 11-15 08:48:47 | 11-16 12:37:23 | 26427637 | 0x60923300… (3) | 27.8 | 0.3398 | 0.0693 | 0.2705 | 0.303 | 25.0 | 10116 | counted | 0.3055 | 0.1549 | 0.1506 |
| 296 | 9.36 | 11-15 11:03:35 | 11-17 18:13:59 | 26436487 | 0x6032d552… (5) | 55.2 | 0.6145 | 0.0437 | 0.5707 | 0.253 | 23.0 | 115824 | counted | 0.2562 | 0.1307 | 0.1255 |
| 370 | 8.19 | 11-15 14:41:11 | 11-17 18:13:59 | 26436487 | 0x6032d552… (5) | 51.5 | 0.5023 | 0.0437 | 0.4585 | 0.253 | 26.0 | 91968 | counted | 0.2534 | 0.1307 | 0.1227 |
| 483 | 6.66 | 11-15 21:37:47 | 11-17 18:13:59 | 26436487 | 0x6032d552… (5) | 44.6 | 0.3537 | 0.0437 | 0.3099 | 0.253 | 32.0 | 45372 | counted | 0.2537 | 0.1307 | 0.1231 |
| 530 | 9.25 | 11-15 11:20:47 | 11-17 18:13:59 | 26436487 | 0x6032d552… (5) | 54.9 | 0.6044 | 0.0437 | 0.5607 | 0.253 | 23.0 | 114792 | counted | 0.2533 | 0.1307 | 0.1226 |
| 633 | 8.43 | 11-15 13:50:35 | 11-17 18:13:59 | 26436487 | 0x6032d552… (5) | 52.4 | 0.5256 | 0.0437 | 0.4819 | 0.253 | 25.5 | 96804 | counted | 0.2558 | 0.1307 | 0.1252 |
| 72 | 3.47 | 11-17 03:55:47 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 26.6 | 0.1101 | 0.0303 | 0.0798 | 0.206 | 50.0 | -84132 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 74 | 2.31 | 11-17 07:10:59 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 23.4 | 0.0643 | 0.0303 | 0.0340 | 0.206 | 75.0 | -185844 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 89 | 2.49 | 11-17 17:22:47 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 13.2 | 0.0391 | 0.0303 | 0.0087 | 0.206 | 70.0 | -204552 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 95 | 5.08 | 11-16 08:23:47 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 46.2 | 0.2791 | 0.0303 | 0.2488 | 0.206 | 34.5 | 41988 | counted | 0.2086 | 0.1085 | 0.1000 |
| 283 | 3.98 | 11-16 22:29:47 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 32.1 | 0.1519 | 0.0303 | 0.1216 | 0.206 | 43.5 | -41172 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 315 | 4.15 | 11-16 18:35:35 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 36.0 | 0.1776 | 0.0303 | 0.1473 | 0.206 | 42.0 | -21720 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 329 | 3.26 | 11-17 07:46:35 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 22.8 | 0.0884 | 0.0303 | 0.0581 | 0.206 | 53.5 | -110580 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 350 | 5.01 | 11-16 08:23:47 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 46.2 | 0.2755 | 0.0303 | 0.2452 | 0.206 | 35.0 | 40188 | counted | 0.2089 | 0.1085 | 0.1003 |
| 351 | 5.0 | 11-16 09:05:11 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 45.5 | 0.2708 | 0.0303 | 0.2405 | 0.206 | 35.0 | 37704 | counted | 0.2084 | 0.1085 | 0.0999 |
| 418 | 4.22 | 11-16 18:35:35 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 36.0 | 0.1808 | 0.0303 | 0.1505 | 0.206 | 41.5 | -19920 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 449 | 3.08 | 11-17 11:30:35 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 19.1 | 0.0699 | 0.0303 | 0.0395 | 0.206 | 56.5 | -134820 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 465 | 5.73 | 11-16 03:17:23 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 51.3 | 0.3496 | 0.0303 | 0.3193 | 0.206 | 30.5 | 74772 | counted | 0.2080 | 0.1085 | 0.0994 |
| 474 | 3.09 | 11-17 11:19:23 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 19.2 | 0.0707 | 0.0303 | 0.0404 | 0.206 | 56.5 | -134148 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 486 | 3.1 | 11-17 11:11:35 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 19.4 | 0.0714 | 0.0303 | 0.0410 | 0.206 | 56.0 | -131880 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 505 | 5.75 | 11-16 02:38:11 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 51.9 | 0.3552 | 0.0303 | 0.3249 | 0.206 | 30.5 | 77124 | counted | 0.2087 | 0.1085 | 0.1001 |
| 509 | 3.42 | 11-17 04:39:59 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 25.9 | 0.1055 | 0.0303 | 0.0752 | 0.206 | 51.0 | -90384 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 510 | 2.82 | 11-17 17:40:59 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 12.9 | 0.0433 | 0.0303 | 0.0130 | 0.206 | 61.5 | -175044 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 512 | 3.27 | 11-17 07:39:11 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 22.9 | 0.0892 | 0.0303 | 0.0588 | 0.206 | 53.0 | -108336 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 544 | 5.65 | 11-16 03:17:23 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 51.3 | 0.3451 | 0.0303 | 0.3147 | 0.206 | 31.0 | 72972 | counted | 0.2086 | 0.1085 | 0.1001 |
| 559 | 5.66 | 11-16 03:17:23 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 51.3 | 0.3457 | 0.0303 | 0.3153 | 0.206 | 31.0 | 72972 | counted | 0.2090 | 0.1085 | 0.1005 |
| 575 | 3.46 | 11-17 04:04:59 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 26.5 | 0.1089 | 0.0303 | 0.0786 | 0.206 | 50.5 | -86484 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 580 | 3.43 | 11-17 04:28:59 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 26.1 | 0.1066 | 0.0303 | 0.0762 | 0.206 | 50.5 | -87924 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 586 | 3.4 | 11-17 04:59:23 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 25.6 | 0.1036 | 0.0303 | 0.0733 | 0.206 | 51.0 | -91548 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 591 | 2.81 | 11-17 17:57:23 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 12.6 | 0.0422 | 0.0303 | 0.0119 | 0.206 | 62.0 | -177828 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 594 | 3.4 | 11-17 05:00:35 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 25.6 | 0.1035 | 0.0303 | 0.0732 | 0.206 | 51.0 | -91620 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 601 | 3.38 | 11-17 05:31:47 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 25.0 | 0.1007 | 0.0303 | 0.0703 | 0.206 | 51.5 | -95292 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 602 | 3.38 | 11-17 05:31:47 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 25.0 | 0.1006 | 0.0303 | 0.0703 | 0.206 | 51.5 | -95292 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 636 | 3.32 | 11-17 06:35:11 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 24.0 | 0.0947 | 0.0303 | 0.0644 | 0.206 | 52.5 | -102696 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 646 | 3.16 | 11-17 09:58:47 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 20.6 | 0.0773 | 0.0303 | 0.0470 | 0.206 | 55.0 | -123912 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 662 | 3.44 | 11-17 04:24:47 | 11-18 06:33:35 | 26440174 | 0x3c51a03f… (30) | 26.1 | 0.1070 | 0.0303 | 0.0766 | 0.206 | 50.5 | -87672 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 44 | 2.22 | 11-18 13:41:35 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 20.5 | 0.0541 | 0.0377 | 0.0163 | 0.231 | 88.0 | -243000 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 87 | 2.49 | 11-18 03:10:59 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 31.0 | 0.0920 | 0.0377 | 0.0543 | 0.231 | 78.0 | -169164 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 107 | 2.5 | 11-18 02:50:47 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 31.3 | 0.0934 | 0.0377 | 0.0557 | 0.231 | 77.5 | -166152 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 123 | 2.45 | 11-18 04:38:35 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 29.6 | 0.0862 | 0.0377 | 0.0484 | 0.231 | 79.5 | -179820 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 254 | 2.47 | 11-18 03:59:11 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 30.2 | 0.0888 | 0.0377 | 0.0511 | 0.231 | 79.0 | -175656 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 317 | 2.48 | 11-18 03:40:23 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 30.5 | 0.0900 | 0.0377 | 0.0523 | 0.231 | 78.5 | -172728 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 323 | 2.43 | 11-18 05:26:47 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 28.7 | 0.0830 | 0.0377 | 0.0453 | 0.231 | 80.0 | -184512 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 327 | 2.36 | 11-18 07:44:23 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 26.5 | 0.0743 | 0.0377 | 0.0366 | 0.231 | 82.5 | -201768 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 330 | 2.2 | 11-18 13:41:35 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 20.5 | 0.0537 | 0.0377 | 0.0160 | 0.231 | 88.5 | -244800 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 331 | 2.47 | 11-18 04:01:23 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 30.2 | 0.0886 | 0.0377 | 0.0509 | 0.231 | 79.0 | -175788 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 333 | 2.47 | 11-18 03:55:23 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 30.3 | 0.0890 | 0.0377 | 0.0513 | 0.231 | 78.5 | -173628 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 339 | 2.48 | 11-18 03:41:47 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 30.5 | 0.0899 | 0.0377 | 0.0522 | 0.231 | 78.5 | -172812 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 341 | 2.47 | 11-18 04:04:35 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 30.1 | 0.0884 | 0.0377 | 0.0507 | 0.231 | 79.0 | -175980 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 342 | 2.46 | 11-18 04:27:11 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 29.7 | 0.0869 | 0.0377 | 0.0492 | 0.231 | 79.0 | -177336 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 364 | 2.46 | 11-18 04:08:11 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 30.1 | 0.0882 | 0.0377 | 0.0505 | 0.231 | 79.0 | -176196 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 502 | 2.12 | 11-18 20:34:47 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 13.6 | 0.0343 | 0.0377 | -0.0034 | 0.231 | 92.0 | -282192 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 555 | 2.45 | 11-18 04:43:59 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 29.5 | 0.0858 | 0.0377 | 0.0481 | 0.231 | 79.5 | -180144 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 568 | 2.21 | 11-18 13:41:35 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 20.5 | 0.0540 | 0.0377 | 0.0162 | 0.231 | 88.0 | -243000 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 578 | 2.48 | 11-18 03:45:35 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 30.4 | 0.0897 | 0.0377 | 0.0520 | 0.231 | 78.5 | -173040 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 622 | 2.29 | 11-18 10:11:11 | 11-19 10:11:35 | 26448445 | 0x0542fbaf… (20) | 24.0 | 0.0656 | 0.0377 | 0.0278 | 0.231 | 85.0 | -219576 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 357 | 1.91 | 11-19 03:15:11 | 11-21 00:22:35 | 26459861 | 0x7a0fb231… (5) | 45.1 | 0.1025 | 0.0436 | 0.0588 | 0.196 | 86.5 | -148956 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 584 | 2.0 | 11-18 22:43:47 | 11-21 00:22:35 | 26459861 | 0x7a0fb231… (5) | 49.6 | 0.1180 | 0.0436 | 0.0743 | 0.196 | 83.0 | -120072 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 600 | 1.91 | 11-19 03:15:11 | 11-21 00:22:35 | 26459861 | 0x7a0fb231… (5) | 45.1 | 0.1025 | 0.0436 | 0.0588 | 0.196 | 87.0 | -150756 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 606 | 1.98 | 11-18 23:40:11 | 11-21 00:22:35 | 26459861 | 0x7a0fb231… (5) | 48.7 | 0.1146 | 0.0436 | 0.0710 | 0.196 | 83.5 | -125256 | not_takeable | 0.0000 | 0.0000 | 0.0000 |
| 610 | 1.99 | 11-18 22:56:59 | 11-21 00:22:35 | 26459861 | 0x7a0fb231… (5) | 49.4 | 0.1172 | 0.0436 | 0.0735 | 0.196 | 83.0 | -120864 | not_takeable | 0.0000 | 0.0000 | 0.0000 |

### Last 361 days (402 occurrences in 317 transactions, 11 senders; rows in `y361-occurrences.md`)

| | n | gross USDC | gas USD | net USD |
|---|---|---|---|---|
| incumbents, as taken | 402 | 179.03 | 37.58 | 141.45 |
| bot, counted class (all positive net) | 94 | 65.25 | 12.50 | **52.75 = 0.146 USD/day** |
| bot, not takeable | 308 | 0 | 0 | 0 |

Counted windows: minimum 168 s (14 blocks), median 9,696 s (808 blocks); 11 of 94 under 1 h. With windows under 30 min
dropped: 90 rows, net 52.09 USD (0.144 USD/day). Concentration: 3 rows carry 41.61 of the 52.75 USD, and 40.55 of it is
one transaction (0x010f3bec…d0c33, block 25,386,151, 2026-06: ids 8 and 29, positions 3,808 and 1,907 USDC, taken by
0x00008004 10.4 h into the ramp; the bot at 6 h: 27.20 + 13.62 USDC gross). By month (counted net USD): 2025-12 1.24,
2026-01 2.05, 03 0.51, 05 1.85, 06 41.00, 07 0.56, 08 0.54, 09 0.29, 10 1.96, 11 2.73.

### What the table shows about the competition

- 0x00008004…bb52 (235 of 402 takes, 146.27 USDC) sweeps dust when a position's reward reaches about 0.30 USDC and
  batches; the bot's threshold (0.14 - 0.28 USDC at these gas prices) is lower, which is why 22 dust rows are counted
  at about 0.12 USD each.
- **A faster taker exists for large positions.** Id 703 (4,843.74 USDC, 5.77 USD/h) was taken by 0x9fe5f3ee…6510
  696 s after its ramp start for 1.11 USDC (tx 0x749de1ab1b1893f6b971485831a26c519526915f5429d2cf996e4016dd1c6429,
  block 26,366,591, 2026-11-08). The bot's 6 h point would have come 20,904 s too late: row `not_takeable`. So the
  manifest's earlier statement "every incumbent take came 10.3 h or more after the start" is false for the last 30
  days, and the forward value of the December cluster (positions of 500 - 8,381 USDC) at the 6 h point is 0 if that
  taker is still active. It is one sample.
- No send rule fixes this (`occ_alt.py`, same occurrences, no lag, send when the reward reaches k x the threshold):
  k = 1: 0.059 USD/day over 361 d (0.106 over 30 d); k = 2: 0.023; k = 3: 0.013; k = 10: 0.021. A lower threshold than
  the incumbents' wins the take but earns only the margin over gas. `LAG_S` was therefore left unchanged (no retuning
  to history); the mechanism pays 0.06 - 0.15 USD/day whichever rule is used.

Against that: the read cost is 0.013 - 0.015 USD/day and a failed private send costs nothing, so the bot is net positive
but small. Lead 391 carries the numbers.

## Read cost

Live Alchemy CU/day: 865 `eth_call` x 26 CU once a day = 22,500, plus at most 48 x 5 x 26 = 6,200 while a dust position
waits under gas: about 25,000-29,000 CU/day = 0.013-0.015 USD at 1M CU = 0.53 USD. Hard cap 60,000 CU/day in code.
No feed filter.

## Money

No principal. Gas only: one restake cost 314,487 gas on the fork (about 0.11 USD at 0.22 gwei); incumbent batches run
about 140k gas per id. Worst case per transaction 2.5M gas x 3 gwei = 0.0075 ETH. Profit arrives as USDC in the bot wallet.

## Files

- `bot.py`, `run.sh`, `executor-runtime.hex` (paper code override = `eth_getCode` of the fork deployment)
- executor source: `scratch/sherlock-arb-ethereum/contracts/src/SherlockArb.sol`; proof: `scratch/sherlock-arb-ethereum/proof.py`, `proof.json`
- logs: `logs/bot.jsonl` (`start`, `scan`, `sleep`, `opportunity`, `opportunity_skip`, `paper_sim`, `position_left_ramp`,
  `send_result` with won / lost / private_not_included, gas used)
