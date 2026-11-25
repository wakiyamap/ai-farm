trial: SPACE / xSPACE lockbox arbitrage on Polygon (cheap-chain trial, decision 2026-11-17-cheap-chain-trials)

## What it does

xSPACE (0x1D1498166DDCEeE616a6d99868e1E0677300056f) is the xERC20 (bridgeable) form of SPACE
(0xB53Ec4aCe420a62Cfb75aFdEba600D284777cd65). The verified `XERC20Lockbox` 0x3267263E005F82A70867B567D4FF06D7E9C52ECf
turns one into the other 1:1 for anyone, with no fee and no limit: `deposit(uint256)` takes SPACE and mints xSPACE,
`withdraw(uint256)` burns xSPACE and pays SPACE (it holds 16.9M SPACE). The two forms trade in different pools:

- SPACE / WPOL on a QuickSwap V2 pair 0xd6ab3f53b1d71837fc1d66b856eeba7b87157e50 (5,723 WPOL + 373,431 SPACE, 0.3 pct)
- xSPACE / WPOL on a Uniswap V3 0.05 pct pool 0xdf6d24718662082e32a63647841cfc91699acd37 (121,816 WPOL + 7.87M xSPACE)

A trade on one pool leaves the other behind. One transaction, funded by a Morpho Blue flash loan of WPOL (no fee),
closes the gap:

- `wrap`: WPOL -> SPACE (QuickSwap) -> lockbox deposit -> xSPACE -> WPOL (Uniswap V3)
- `unwrap`: WPOL -> xSPACE (Uniswap V3) -> lockbox withdraw -> SPACE -> WPOL (QuickSwap)

The bot waits on the farm feed for a `Swap` on either pool. On an event it asks the executor, in one `eth_call`
(`probe`), what each route would gain at 20 / 60 / 150 / 400 / 800 WPOL. If the best gain is above the gas cap of the
send (`gasLimit x maxFeePerGas`), it simulates the exact call and (live) sends it with `minProfit = cap`. The executor
reverts unless the WPOL balance grew by `minProfit`, unwraps the gain and pays it to the bot wallet as POL.

## Competition, last 7 days (blocks 97,377,559-97,680,063)

Source: `scratch/rcdd0/takes.py` on the lockbox's `Deposit(address,uint256)` (topic0 0xe1fffcc4...) and
`Withdraw(address,uint256)` (0x884edad9...) events: 8 events in 7 days, every one an atomic arbitrage.

| block | direction | sender -> contract | tx index | gas used x price | kept (WPOL) |
|---|---|---|---|---|---|
| 97,426,942 | wrap | 0x1f96ec88 -> 0x0b3a59ee | 75 | 333,972 x 281 gwei | 0.381 |
| 97,455,986 | unwrap | 0xf3f7364c -> 0x5f81f56a | 15 | 373,667 x 323 gwei | 0.382 |
| 97,483,547 | unwrap | 0xf3f7364c -> 0x5f81f56a | 33 | 386,092 x 324 gwei | 0.433 |
| 97,657,033 | wrap | 0xf3f7364c -> 0x5f81f56a | 25 | 373,168 x 336 gwei | 33.284 |
| 97,660,003 | unwrap | 0xf3f7364c -> 0x5f81f56a | 29 | 379,358 x 328 gwei | 4.807 |
| 97,660,033 | wrap | 0xf3f7364c -> 0x5f81f56a | 64 | 384,801 x 328 gwei | 1.623 |
| 97,678,142 | unwrap | 0xf3f7364c -> 0x5f81f56a | 23 | 366,941 x 329 gwei | 0.471 |
| 97,678,169 | wrap | 0xf3f7364c -> 0x5f81f56a | 21 | 373,276 x 381 gwei | 0.315 |

Two operators (0xf3f7364c818f996bcfcb83802523d972054d8b2f through the step-runner contract
0x5f81f56a7faaff242a1074cc1ffe0a6de7c69456, 7 takes; 0x1f96ec881d642476975c88fc8eb76c5d243791be through
0x0b3a59ee683e6d32e762839c5b2232d3f49c88fb, 1 take). Sum 41.7 WPOL = 3.15 USD at 0.0756 USD per POL (coins.llama.fi
2026-11-21); gas about 0.12 POL (0.009 USD) a take. Priority fee: about the 30 gwei Polygon minimum (gas price 281-381
gwei on a 250-300 gwei base fee); no bidding.

Blocks to take (`scratch/trial-xspace-arb-polygon/series.py` -> `series-windows.json`: this bot's own `probe()` as a
code override at 1 / 2 / 3 / 5 / 10 / 30 / 100 / 300 / 2000 blocks before each take; a block is about 2 s):

| take | best gain (WPOL) at -1 / -2 / -3 / -5 / -10 / -30 / -100 blocks | stood at least |
|---|---|---|
| 97,426,942 | 0.95 / 0.95 / 0.13 / 0.13 / 0.13 / 0.13 / 0.13 | 2 blocks |
| 97,455,986 | 1.06 / 1.06 / 1.06 / 1.06 / 0.60 / 0.13 / 0.13 | 10 blocks |
| 97,483,547 | 0.41 / 0.41 / 0.41 / 0.41 / 0.41 / 0.41 / 0.41 | 100 blocks |
| 97,657,033 | 46.80 / 60.24 / 70.33 / 0.06 / 0.06 / 0.06 / 0.06 | 3 blocks |
| 97,660,003 | 6.47 / 26.17 / 50.58 / 0.15 / 0.15 / 0.15 / 0.15 | 3 blocks |
| 97,660,033 | 4.80 / 4.80 / 4.80 / 4.80 / 4.80 / 0.43 / 0.15 | 10 blocks |
| 97,678,142 | 6.00 / 6.00 / 13.20 / 0.00 / 0.08 / 0.08 / 0.08 | 3 blocks |
| 97,678,169 | 0.95 / 0.95 / 0.95 / 0.95 / 0.95 / 13.20 / 0.08 | 10 blocks |

Median 3-10 blocks (6-20 s), minimum 2 blocks (4 s). The large gaps open 3-4 blocks (6-8 s) before the incumbent's
take and shrink every block (70 -> 60 -> 47 WPOL), so other traders eat part of them first. The incumbent takes with a
fixed small size: at the parents of its takes this bot's best size found 46.8 WPOL where it kept 33.3, and 6.0 where
it kept 0.47. A feed bot (log delivered about 1 s after the block, next-block send) arrives inside these windows; the
farm's 3 s reaction time is shorter than every window measured here.

## Addresses

- XERC20Lockbox 0x3267263E005F82A70867B567D4FF06D7E9C52ECf: Etherscan-verified source read
  (`scratch/r2f37/src-staker`); `XERC20()`, `ERC20()`, `IS_NATIVE()` answer xSPACE, SPACE, false.
- From the incumbent's calldata (tx 0xf76c3405ecda8f145a9b1a025ca6e618e54833d90738c109fcbeea8c23f363b2), each with a
  getter answering (`scratch/trial-xspace-arb-polygon/sigs.py`): Morpho Blue 0x1bF0c2541F820E775182832f06c0B7Fc27A25f67
  (holds 926,533 WPOL), QuickSwap V2 router 0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff (`factory()` = the pair's
  factory 0x57573714...), Uniswap V3 SwapRouter02 0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45 (`factory()` = the pool's
  factory 0x1F98431c...), WPOL 0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270.

## Loss bound

A lost attempt costs gas only: at most `gasLimit x maxFeePerGas`, about 0.24 POL (0.018 USD) at a 250 gwei base fee
(gas limit = estimate x 1.2 = about 685,000; max fee = base fee x 1.25 + 30 gwei). The code refuses a send whose cap
is 0.95 USD or more at 0.15 USD per POL, a gas limit above 900,000 and a max fee above 1,500 gwei. `capital_usd` 5 is
the whole budget: about 250 lost attempts.

## Read cost

- Feed: one `/logs` filter (2 addresses, 2 topic0 values), 72 Swap logs a day x about 900 bytes x 0.04 = 2,600 CU,
  plus about 4 CU/min while subscribed = 5,800 CU: about 8,400 feed CU/day. Polygon had 3 of 16 filters before this
  bot.
- Relay: safety poll every 5 min = 288 x 26 CU = 7,500; one probe per feed event = 72 x 26 = 1,900; up to three
  follow-up probes (10 / 30 / 90 s) after a look that saw a gain, and 66 CU (block, estimate, guard simulation) per
  opportunity: about 2,000. About 11,400 relay CU/day.
- Total about 20,000 CU/day = 0.011 USD/day at 0.53 USD per million CU. Code cap 95,000 CU/day (then it sleeps to
  00:00 UTC).

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `feed_subscribed`, `feed` (blocks, txs, block timestamps), `feed_gap`, `feed_error`,
`check` (trigger, no_gain), `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`, `send_result` (won /
lost, gas used, send block, winner block = the block of the newest lockbox Deposit / Withdraw, tx index),
`signer_reject`, `read_budget`, `loop_error`.

## Not covered

Only the two pools the incumbent uses are routed. The class is small (about 42 WPOL = 3 USD in 7 days for everyone) and
ends if the QuickSwap pair is drained or SPACE liquidity moves to xSPACE entirely. In paper mode a standing gap is
logged again at every look, because nothing takes it.
