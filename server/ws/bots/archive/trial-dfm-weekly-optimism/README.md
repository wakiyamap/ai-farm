trial: defi.money weekly fee distribution caller incentive on OP Mainnet (10 MONEY once per protocol week, weeks start Sunday 12:00:00 UTC).

## What pays

`PrimaryFeeAggregator.processWeeklyDistribution()` (verified source, comment "unguarded external functions") can run
once per protocol week and transfers `callerIncentive` = 10 MONEY to `msg.sender` when the aggregator holds more than
20 MONEY. The aggregator is filled by two other public calls: `PegKeeperRegulator.withdraw_profit()` (every keeper
removes its profit from its Curve pool, the coins go to the FeeConverter) and `FeeConverter.transferToAggregator()`.
The executor does all three, sells the 10 MONEY for USDC on the Curve USDC / MONEY pool, sends the USDC to the bot
wallet and reverts unless the wallet's USDC grew by `minProfit`.

Next window: **Sunday 2026-11-29 12:00:00 UTC** (week 127). That is after the trials' close on 11-24: a live bot
has nothing to do before it. It also meets the non-trial rule for a scheduled window (table below: every past take
came at least 12 s after the week start, three weeks were never taken), so the reviewer or the human may keep it.

## Last 7 days of competition (and the 9 weeks before, block timestamps)

| week | start (UTC) | taken after | caller | tx index | this bot's tx simulated at the first block of the week |
|---|---|---|---|---|---|
| 126 | 2026-11-22 12:00:00 | 13 s (block 159,875,018, 6 blocks after the first one) | 0x953c1ba7 via contract 0x67807260 | 37 | 9.891487 USDC |
| 125 | 2026-11-15 12:00:00 | 36,913 s (10.3 h), block 159,591,068 | 0x953c1ba7 | 16 | 9.866324 USDC |
| 124 | 2026-11-08 12:00:00 | never | - | - | 9.825239 USDC |
| 123 | 2026-11-01 12:00:00 | never | - | - | 9.804616 USDC |
| 122 | 2026-10-25 12:00:00 | never | - | - | 9.817864 USDC |
| 121 | 2026-10-18 12:00:00 | 35 s | 0x9edd211b | not read | 9.904052 USDC |
| 120 | 2026-10-11 12:00:00 | 41 s | 0x9edd211b | not read | 9.919165 USDC |
| 119 | 2026-10-04 12:00:00 | 9,689 s (2.7 h) | 0x4a00e700 | not read | 9.936266 USDC |
| 118 | 2026-09-27 12:00:00 | 249 s | 0x9edd211b | not read | 9.932927 USDC |

Median of the six taken weeks: 145 s; minimum 13 s (6 blocks of 2 s). Sources: `eth_getLogs` of
`ProcessWeeklyDistribution` on the aggregator over 4,000,000 blocks (`scratch/r21d6/dfm_state.py`, 7 events, 10 MONEY
each) and `scratch/trial-dfm-weekly-optimism/weeks.py` (`weeks-result.json`). In the last 7 days: one take, by
0x953c1ba7, effective gas price about 0.002 gwei (its whole fee was 2.8e-6 ETH = 0.005 USD for 1,390,025 gas; the
priority part was not split out). This bot bids a fixed 0.005 gwei priority fee. The dates in
the table are computed from the week formula, the "taken after" values from block timestamps.

The bot aims at every week: it simulates once a second from 2 s before the week start and sends in the first second
the simulation passes (the first block whose timestamp is at or after the start), about 2-4 s after it.

## Addresses (OP Mainnet)

- PrimaryFeeAggregator `0xfeea66de54c040cf8323bc6f2f83c1ba70aacab9`: verified source (explorer), `lastDistributionWeek()` = 126, `callerIncentive()` = 10e18.
- FeeConverter `0xee84dd92653a66bf342d52aa0913a2eab3b5c2fe`: verified source, `transferToAggregator()`.
- PegKeeperRegulator `0xe7e7185c801d28197cbc8d724f67f402d948c0c1`: from the incumbent's trace (it calls `withdraw_profit()` on five keepers) and KB protocols:878.
- MONEY `0x69420f9e38a4e60a62224c489be4bf7a94402496` (`symbol()` MONEY), USDC `0x0b2c639c533813f4aa9d7837caf62653d097ff85`.
- Curve pool `0x8f63ccd329d4ba07a3c6703d94d3137a9cfbfc6c`: `coins(0)` = USDC, `coins(1)` = MONEY; 20.68 USDC + 27.65 MONEY on 2026-11-22, `get_dy(1, 0, 10 MONEY)` = 9.894979 USDC. The pool is small: if it is drained the simulation shows less and `minProfit` (half the simulated gross, at least the gas cap) decides.
- GasPriceOracle predeploy `0x420000000000000000000000000000000000000F` (`decimals()` = 6 answers).

## Read cost

Week already distributed: one `eth_call` when the bot starts or a week ends, then no reads until the next week
start. At the week start: at most 122 looks of 26 CU (plus 4 reads when one passes) = about 3,300 CU once a week.
Week open and undistributed: one look every 10 minutes = 144 x 26 = 3,744 CU a day. Worst day about 7,100 CU =
0.004 USD at 1M CU = 0.53 USD; the bot stops reading at 60,000 CU a day. No feed filter (the trigger is the clock).

## Loss bound

A lost send reverts in the aggregator ("Already distro'd this week") after about 0.33M gas; the bound per send is
gas limit (estimate x 1.3, at most 2.5M) x maxFeePerGas (2 x base fee + 0.005 gwei, never above 2 gwei) plus twice
the L1 data fee from the GasPriceOracle: about 7.8e-6 ETH = 0.031 USD at 4,000 USD per ETH on 2026-11-22. At most 3
sends per week. Profit arrives as USDC in the bot wallet; the executor keeps nothing.

## Files

`bot.py` (paper and live in one file; live needs `EXECUTOR_ADDR_OPTIMISM` or `EXECUTOR_ADDR`), `run.sh`,
`executor-runtime.hex` (paper code override = `eth_getCode` of the fork deployment), `manifest.yaml`.
Proof and measurements: `scratch/trial-dfm-weekly-optimism/` (`proof.py`, `selftest.py`, `weeks.py`, `setup.py`).
