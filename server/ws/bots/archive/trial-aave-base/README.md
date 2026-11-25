trial

# trial-aave-base

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): Aave v3 Base liquidations of the public,
non-Atlas class. Win rate is measured by sending; nothing here counts as expected revenue under the race rule.

## What it does

1. Waits on the farm feed for `LiquidationCall` on the Aave v3 Pool `0xa238dd80c259a72e81d7e4664a9801593f98d1c5`
   (topic0 `0xe413a321...5286`). One liquidation usually means a price flip that put other users under water.
2. On an event (and about every 60 s as a safety poll, hourly over the whole universe) reads
   `getUserAccountData` for the near-HF list in one Multicall.
3. For a user with HF < 1 and debt >= 5 USD it simulates the exact executor call for each supported pair
   (debt USDC or WETH; collateral WETH, cbBTC or USDC; UniV3 fee 500 then 3000) and keeps the best.
4. Live: sends `liquidate(...)` on its executor when simulated gross > the signed gas cap. The executor
   flash-borrows the cover from Morpho, calls `liquidationCall`, swaps the seized collateral on UniV3,
   repays, and reverts unless the debt-token balance grew by `minProfit` (= the gas cap). Paper: logs `paper_sim`.

## Competition, last 7 days (to 2026-11-17, attempts:1669, `scratch/trial-aave-base/census.json`)

- 261 `LiquidationCall` events in 173 txs.
- 79 txs / 153 events enter through the Atlas OEV metacall `0x583dcfef0d240dc80753f0f0b26513fee27d9b77`
  (price update delivered inside the winner's tx). Not reachable by this bot.
- Public class: 94 txs / 108 events, about 12 entry contracts (`0xf15bc3b0` 24 txs, `0x5ac9bc14` 20,
  `0xb091bc76` 13, `0x16e41af5` 12, Pool called directly 10, seven others 1-3 each).
- Blocks to take: 14 of 16 sampled public captures flipped inside the capture block (tx index 2-6);
  2 of 16 were under water 3 blocks (0.6 s) before being taken.
- Priority fees: 0.05-779 gwei, scaling with size. Covers of 30-75 USDC paid 0.8-2 gwei; the 52,684 USDC
  cover paid 779 gwei; the two straggler captures paid 0.05 and 1.97 gwei.
- Mechanism: the Aave-facing WETH source `0x9da00d23...` lags its inner feed `0xd772f6d9...` (new answer
  visible >= 3 blocks earlier at block 57496516-57496519, `scratch/trial-aave-base/oracle.py`), so fast
  takers pre-position for the flip block. This bot does not; it reacts to confirmed logs.

This bot bids at most 50% of simulated gross and never signs more than 0.90 USD of gas, so it can only win
small or neglected cases (stragglers, users left under water after a cascade).

## Loss bound

- Executor reverts unless the gain >= `minProfit`; a lost attempt costs gas only (about 285k-625k gas,
  0.003-0.005 USD at 0.008 gwei).
- `maxFeePerGas x gasLimit + 0.02 USD` (L1 fee allowance) < 0.90 USD per send, `maxFeePerGas` <= 0.5 gwei.
- Wallet holds gas only (15 USD, under the 18 USD Base cap). No principal: the cover is a Morpho flash loan.

## Read cost

- Relay: near scan 1440 x 26 CU = 37,440; full scan 27 calls x 24 x 26 = 16,848; discovery 144 x 70 = 10,080;
  about 64,000 CU/day, hard-capped in code at 75,000 CU per UTC day.
- Feed: `/logs/base` filter address = Pool, topic0 = LiquidationCall, about 37 events/day, about 7,000 CU/day.
- Total about 71,000 CU/day = 0.04 USD/day at 1M CU = 0.53 USD.
- On feed `gap`, 429, 503 or timeout the bot re-reads the near list through the relay.

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (with `executor=`), `discover`, `scan`, `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`,
`paper_sim`, `send`, `send_result` (`result` won/lost, `gas_used`, `send_block`, `winner_block`, `winner_tx`,
`blocks_after_winner`), `signer_reject`, `feed_error`, `read_budget`.

## Fork proof

`scratch/trial-aave-base/proof.py` (reset base 57496521, deploy, guards, success +1.446070 USDC, exhausted);
`scratch/trial-aave-base/selftest.py` checks the bot's calldata against `cast calldata` and the paper override.

## Files

`bot.py`, `run.sh`, `executor-runtime.hex` (paper code override, `eth_getCode` of the fork deployment),
`seed-users.json` (5,299 borrowers: archived aave-watcher-base candidates + users liquidated in 30 d).

## Cover sweep (added 2026-11-17, run 039e2c1e)

For a debt of 2,000 USD or more the bot no longer simulates one size only. Per collateral and fee tier it tries
103, 50, 25, 12, 6 and 3 % of the debt, largest first, and stops at the first size that gains less than the one
before; the best size over all routes is sent. Reason: the seized collateral is sold in one UniV3 pool, and past
some size the slippage is larger than the liquidation bonus, so the flash-loan repayment fails (Morpho
`transferFrom reverted`) and the old single size never simulated on the largest borrowers. A revert with
`HealthFactorNotBelowThreshold()` (`0x930bb771`) ends the attempt at once. Debts under 2,000 USD keep the single
full over-cover (a smaller cover on a small debt reverts `MustNotLeaveDust()`).

Evidence (`scratch/aave-sweep-port/`): `regress.py`: the original proof case is unchanged (cover 39.923343 USDC, gain 1.446070 USDC). `harness.py base` over the 8 largest USDC-debt liquidations of the last 1.3M blocks: none was under water at its parent block (same-block oracle captures), so the new code stops after one simulation each (5 reads instead of 6-9). The size effect itself is measured on polygon (`proof_polygon_sweep.py`, +229.827318 USDC where the single size reverts) and on OP Mainnet (`revert_probe.json`); no Base borrower in the window shows it.
Read cost: up to 6 `eth_call` per route and fee tier instead of 1, only for debts of 2,000 USD or more
(about 20 calls = 520 CU for the polygon case above); inside the 75,000 CU/day cap already in the code.
