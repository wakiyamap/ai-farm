trial

# trial-aave2-avalanche

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): liquidations on Aave v2 Avalanche, a frozen
market that still liquidates about 2.7 positions a day (lead 309). Win rate is measured by sending; nothing
here counts as expected revenue under the race rule. Port of the live `trial-aave2-polygon` with its own
executor (different flash source and swap venue).

## What it does

1. Waits on the farm feed for `LiquidationCall` on the Aave v2 LendingPool
   `0x4F01AeD16D97E3aB5ab2B501154DC9bb0F1A5A2C` (topic0 `0xe413a321...5286`).
2. On an event (and about every 60 s as a safety poll, hourly over the whole universe) reads
   `getUserAccountData` for the near-HF list in one Multicall.
3. For a user with HF < 1 and debt >= 2 USD it simulates the exact executor call for each supported pair
   (debt USDC.e, USDT.e or DAI.e; collateral WETH.e, WBTC.e, WAVAX, USDC.e, DAI.e, USDT.e; up to two Trader
   Joe V1 routes per pair, two cover sizes) and keeps the best.
4. Live: sends `liquidate(...)` on its executor when simulated gross > the signed gas cap. The executor
   flash-borrows the cover from the Aave v2 pool itself (`flashLoan`, 9 bps premium; the Balancer vault holds
   no bridged stables on Avalanche), calls `liquidationCall`, sells the seized collateral through Trader Joe
   V1 pairs, lets the pool pull loan + premium, sells the surplus debt token for native USDC
   (`0xB97EF9Ef...`) and reverts unless the USDC balance grew by `minProfit` (= the gas cap). Paper: logs
   `paper_sim`.

## Competition, last 7 days (blocks 100,135,744-100,809,089, attempts:2650 and attempts:2668)

- 19 `LiquidationCall` events in 19 txs by 5 liquidator addresses: `0x988a2540` 8, `0x5ac9bc14` 6,
  `0x9db94915` 2, `0x759bb40c` 2, `0x6ebfb347` 1. Liquidator gross (17 parsed): median 2.56 USD, max 46.77,
  total 126.6 USD.
- Blocks to take (`scratch/trial-aave2-avalanche/parents.json`: HF at capture block -1, -2, -10): 13 of 19
  flipped inside the capture block (3 of them taken at tx index 0); 6 of 19 were already under water at the
  parent block (cover 17.08, 16.40, 4.45, 32.99, 1.88 and 0.60 USD; 73 USD of cover, roughly 3.7 USD of
  bonus per week). Three of the six were also under water two blocks before, one ten blocks before.
- Priority-fee level (`scratch/a2-scout/flows.json`): 12 of 17 winners paid an effective gas price of
  9.8-33 gwei (0.07-0.3 USD per tx at 0.63M-1.7M gas); the 46.8 USD case paid 94.8 gwei; index-0 takes paid
  217 gwei, 1,502 gwei and 2,904 gwei (up to 23.75 USD of gas).
- The incumbents fund the same way: `0x5ac9bc14` flash-borrows from the v2 pool (tx `0x37d6d639...`).

This bot bids at most 50% of simulated gross and never signs more than 0.90 USD of gas. It can only win the
parent-underwater share and small positions left under water for minutes. Expect cents per day at best.

## Limits

- The universe starts from 850 addresses with debt >= 1 USD (`seed-users.json`, built 2026-11-19 by
  `scratch/trial-aave2-avalanche/seed.py`: all 2,097 holder rows of the USDC.e / USDT.e / DAI.e variable debt
  tokens from Routescan, 30 days of pool logs, the census users) and grows from the pool's own logs.
  Borrowers who only owe WAVAX, WETH.e or WBTC.e are not in it.
- 12 seed users with debt >= 2 USD are under water at head and cannot be taken (HF around 1e-9: the
  collateral is gone, Aave error 23 / 44; `scratch/trial-aave2-avalanche/selftest-result.json`). The bot
  retries them every 6 h only (`COOL_NO_ROUTE`).
- Sizing treats USDC.e, USDT.e and DAI.e as 1 USD. Trader Joe V1 pairs are thin for WETH.e and WBTC.e
  (107 WETH.e and 1.09 WBTC.e against WAVAX): fine for the usual 1-1,000 USD covers; larger ones are sized
  down by the sweep or skipped by the simulation.
- USDT.e and DAI.e debt routes are simulated before every send but were not fork-proven on a historical
  case; both proof cases have USDC.e debt.

## Loss bound

- Executor reverts unless the gain >= `minProfit`; a lost attempt costs gas only (0.23M gas when the
  position is gone, about 0.9M when the profit guard trips: 0.01-0.06 USD at 10 gwei).
- `maxFeePerGas x gasLimit` < 0.90 USD per send at the Aave oracle AVAX price, `maxFeePerGas` <= 500 gwei.
- Wallet holds AVAX for gas only (10 USD). No principal: the cover is an Aave v2 flash loan.

## Read cost

- Relay: near scan 1440 x 26 CU = 37,440; full scan 5 calls x 24 x 26 = 3,120; discovery 144 x 70 = 10,080;
  retries of stuck users about 5,000; about 56,000 CU/day, hard-capped in code at 75,000 CU per UTC day
  (then the bot sleeps to 00:00 UTC; the startup read is inside the same handler).
- Feed: `/logs/avalanche` filter address = LendingPool, topic0 = LiquidationCall, about 3 events/day,
  about 2,000 CU/day. Avalanche had 3 of 16 feed filters in use on 2026-11-19.
- Total about 58,000 CU/day = 0.03 USD/day at 1M CU = 0.53 USD.
- On feed `gap`, 429, 503 or timeout the bot re-reads the near list through the relay.

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (with `executor=`), `discover`, `scan`, `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`,
`paper_sim`, `send`, `send_result` (`result` won/lost, `gas_used`, `send_block`, `winner_block`, `winner_tx`,
`blocks_after_winner`), `signer_reject`, `feed_error`, `read_budget`.

## Proof

`scratch/trial-aave2-avalanche/proof.py` (two historical cases, PROOF OK) and `selftest.py`; see
`fork_evidence` in the manifest.
