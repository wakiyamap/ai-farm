trial: USND redemption on Nerite (Liquity V2 fork, Arbitrum) when the DEX price of ETH runs ahead of the price Nerite redeems at. Measures the farm's win rate by sending; it does not earn (whole pot about 0.14 USD/day gross).

## Mechanism

Nerite's `CollateralRegistry.redeemCollateral(uint256,uint256,uint256)` (0x7f7fbc27..., no role) lets anyone burn USND for the branch collaterals at the protocol's oracle price, minus a redemption fee (0.55-0.63% in the last 7 days). USND trades at about 0.997 USDC on the Uniswap V3 USND/USDC pool 0x319b7186.... When ETH jumps on the DEXes and the redemption price has not followed yet, the collateral received is worth more than the USND cost. One executor call:

1. Flash-swap 30-50 USND out of the USND/USDC pool (the pool is owed USDC inside the swap callback).
2. `redeemCollateral(usnd, 10, 1e18)`: WETH (about 93%), wstETH, rsETH, weETH, tBTC arrive.
3. Sell each LST and tBTC for WETH on its Uniswap V3 pool, then all WETH for USDC on WETH/USDC 0.05% (0xc6962004...).
4. Pay the USND pool in USDC; revert `NoProfit` unless the USDC balance grew by `minProfit`; pay the gain to the bot wallet as USDC.

## Competition, last 7 days (blocks 523,077,310-525,496,510)

- 6 redemption transactions (30 Redemption events on the 8 TroveManagers), all by EOA 0x855fb44db86bb50ee8180496a080b45dbb9ba2c7 through its executor 0x22ee214ba643c637401f62af49583eb2283040c7 (selector 0x6ec844b8). Nobody else.
- Size 40 USND (5 takes) or 56 USND (1). Gross 0.142-0.224 USDC per take; gas 2.79m-2.90m at 0.0200-0.0223 gwei = 5.6e-5-6.3e-5 ETH = 0.10-0.11 USD; net 0.03-0.11 USD.
- Priority fee: none (effective gas price = base fee; Arbitrum orders first come first served). Transaction index 2, 2, 8, 11, 20, 61.
- Blocks from takeable to taken (`scratch/trial-nerite-redeem-arbitrum/windows.py` -> `windows.json`, the executor's 40 USND gain by `eth_call` at 1 / 4 / 40 / 240 / 1200 blocks before each take; Arbitrum makes about 4 blocks per second): no gain at all 240 blocks (60 s) before 5 of 6 takes; at 40 blocks (10 s) before, the gain was 0.039-0.138 USDC; at 4 blocks (1 s) before, 0.140-0.161. So the incumbent takes within about 5-15 s of the gain passing its threshold of about 0.14 USDC. Median takeable-to-taken about 10 s (40 blocks), minimum under 1 s.
- What opens it (`why.py` at take 524,218,659): USND pool price 0.997183 and redemption rate 0.55003% were flat for 2 minutes while WETH/USDC went 1820.6 -> 1846.9; the gain went none -> 0.043 (15 s before) -> 0.086 (4 s) -> 0.174 (take). Only 1 of 6 takes followed a swap on the USND pool (18 s after a 100 USND sale); `trigger.py` -> `trigger.json`.
- The price source (`oracle.py`, callTracer of take 0x0b1ac32b...): the WETH branch (93% of a 40 USND redemption) reads `latestRoundData` of 0x4df393fa84e4a0cfdf14ce52f2a4e0c3d1ab0668, an 18-decimal push feed; at that take its answer was 1759.30, 1,076 s old, while WETH/USDC traded at 1774.84 (+0.88%). Estimated from that one take (0.1398 USDC on 40 USND = 0.35%), not measured separately: the gain is zero at a gap of about +0.53% and reaches this bot's cap at about +0.83%.
- This bot's threshold is its signed gas cap, about 0.118-0.121 USDC at those blocks (below the incumbent's 0.14), so it may send one to a few seconds earlier, if its timer lands there. With a 30 s base timer and a 10-40 s span between "gain >= 0.01 USDC" and the incumbent's take, expect it to be in fast mode for about half of the openings.

## Bot

- Base timer 30 s: one `eth_call` of the executor `take(40 USND, minProfit 0)` with a code override (paper) or the live executor. Also checks on `Swap` events of the USND/USDC pool through the feed (15 swaps in 18 h) and on a feed `gap`.
- Fast mode: once a probe shows a gain of 0.01 USDC or more, the timer is 2 s until 40 s after the last such probe; fast mode spends at most 15,000 relay CU per UTC day.
- Near the cap: sizes 30 / 40 / 50 USND, `eth_estimateGas` x 1.10 = gas limit, maxFeePerGas = base fee x 1.05 + 1 wei, cap = gasLimit x maxFee in USD at the WETH/USDC pool price. Sends only when gross > cap, with `minProfit = cap + 1` micro-USDC, after simulating the exact guarded call at the signed gas limit.
- A lost attempt (the incumbent took it first) burns about the whole route's gas, 0.10 USD: capital 10 USD covers about 100 lost sends.
- Logs (`logs/bot.jsonl`): `check`, `fast_mode`, `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`, `send`, `send_result` (won / lost, gas used, winner block and tx).

## Read cost

Base 86,400 / 30 = 2,880 probes x 26 CU = 75k CU/day; fast mode at most 15k; opportunities about 250 CU each. Code cap 93,000 relay CU/day = 0.05 USD/day at 0.53 USD per million CU. One feed filter (USND/USDC pool Swap, about 20 events a day).

## Evidence

`scratch/trial-nerite-redeem-arbitrum/`: `proof.py` + `proof-result.json` (fork), `selftest.py` (calldata against `cast calldata`, the bot's check at fixed blocks), `windows.py`, `why.py`, `trigger.py`, `oracle.py`, `fastmode_test.py`; 7-day events in `scratch/nerite/red-logs.json` (`scan.py`, `txs.py`).
