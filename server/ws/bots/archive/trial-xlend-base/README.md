trial

# trial-xlend-base

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): liquidations on XLend (Extra Finance, an Aave v3
fork) on Base, Pool `0x09b11746dfd1b5a8325e30943f8b3d5000922e03`. Win rate is measured by sending; nothing here
counts as expected revenue under the race rule. Built from lead 266, measurement in attempts:2047.

## What it does

1. Waits on the farm feed for `LiquidationCall` (topic0 `0xe413a321...5286`) on two addresses: the XLend Pool and
   the Aave v3 Base Pool `0xa238dd80c259a72e81d7e4664a9801593f98d1c5`. The Aave pool is a wake-up signal only
   (about 37 events/day: a price flip that liquidates Aave users also moves XLend health factors); the bot never
   calls it.
2. On an event (and about every 60 s as a safety poll, hourly over the whole universe of 1,015 borrowers) reads
   `getUserAccountData` for the near-HF list in one Multicall.
3. For a user with HF < 1 and debt >= 5 USD it simulates the exact executor call for each supported pair
   (debt USDC or WETH; collateral WETH, cbBTC, USDC, cbETH, wstETH or AERO; UniV3 fee 500, 3000, 100) and keeps
   the best. A route without a UniV3 pool just fails its simulation.
4. Live: sends `liquidate(...)` on its executor when simulated gross > the signed gas cap. The executor
   flash-borrows the cover from Morpho, calls `liquidationCall`, swaps the seized collateral on UniV3, repays, and
   reverts unless the debt-token balance grew by `minProfit` (= the gas cap). Paper: logs `paper_sim`.

Not covered: EURC or cbBTC debt (the profit would arrive as a token the farm does not count); 2 of the 7 events
of the last 7 days had such debt.

## Competition, last 7 days (to 2026-11-18, attempts:2047)

- 7 `LiquidationCall` events in 5 txs (`scratch/xlend-liq7d.json`), about 1 per day. Every one went through
  router `0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd`, sent by 3 EOAs (`0xd9fffdf0` 3 txs, `0xe319d3a8` 1,
  `0x82885e6f` 1). No Atlas / OEV class on this pool.
- Position in block: tx index 2, 3, 4, 7, 9.
- Blocks to take (`scratch/trial-xlend-base/hf.json`, health factor read at blocks before each capture):

| capture block | debt | HF at -1 / -2 | HF at -5 | takeable for | winner tip |
|---|---|---|---|---|---|
| 56757757 | 59.7 USD (EURC) | 0.99903 | 1.00230 | 2-4 blocks (0.4-0.8 s) | 0.083 gwei |
| 56778471 | 209.3 USD (USDC) | 0.999995 | 1.00193 | 2-4 blocks (0.4-0.8 s) | 0.149 gwei |
| 57164783 | 39.7 USD (USDC) | 0.99756 | 1.00285 | 2-4 blocks (0.4-0.8 s) | 0.102 gwei |
| 57503669 | 237.3 USD (cbBTC) | 1.00511 | 1.00511 | 0 (flipped in the capture block) | 1.471 gwei |
| 58096109 | 0.38 USD dust (USDC) | 0.909 | 0.909 | more than 30,000 blocks (100 min) | 0.001 gwei |

- Priority fees: 0.08-0.15 gwei on the 40-210 USD cases, 1.47 gwei on the same-block case, 0.001 gwei on dust
  (`scratch/trial-xlend-base/receipts.json`). Winner gas 726k-1.42M.

The winners are 0.4-0.8 s behind the price update, the farm reacts in about 3 s, so this bot loses a clean
race; it can win when the router is late or absent (the dust case shows the pool is not watched closely) and on
users left under water after a cascade. For the proof case the bot would have bid a 0.446 gwei tip (winner paid
0.149).

## Loss bound

- Executor reverts unless the gain >= `minProfit`; a lost attempt costs gas only (about 370k-770k gas,
  0.004-0.006 USD at 0.006 gwei).
- `maxFeePerGas x gasLimit + 0.02 USD` (L1 fee allowance) < 0.90 USD per send, `maxFeePerGas` <= 0.5 gwei;
  the tip is at most 50% of simulated gross.
- Wallet holds gas only (15 USD, under the 18 USD Base cap). No principal: the cover is a Morpho flash loan.

## Read cost

- Relay: near scan 1440 x 26 CU = 37,440; full scan 6 calls x 24 x 26 = 3,744; discovery 144 x 70 = 10,080;
  about 51,000 CU/day, hard-capped in code at 75,000 CU per UTC day.
- Feed: `/logs/base`, addresses = XLend Pool + Aave v3 Pool, topic0 = LiquidationCall, about 38 events/day,
  about 7,000 CU/day.
- Total about 58,000 CU/day = 0.03 USD/day at 1M CU = 0.53 USD.
- On feed `gap`, 429, 503 or timeout the bot re-reads the near list through the relay.

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (with `executor=`), `discover`, `scan`, `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`,
`paper_sim`, `send`, `send_result` (`result` won/lost, `gas_used`, `send_block`, `winner_block`, `winner_tx`,
`blocks_after_winner`), `signer_reject`, `feed_error`, `read_budget`.

## Fork proof

`scratch/trial-xlend-base/proof.py`: reset base 56778470 (parent of the historical capture `0xac759210...`),
deploy, NotOwner, NoProfit, success +6.810296 USDC (gas 673,330), second call reverts `Error("45")`.
`scratch/trial-xlend-base/selftest.py`: the bot's calldata equals `cast calldata`; relay `eth_call` at 56778470
with the paper override returns 6.810298 USDC; `attempt()` replayed at that block logs `opportunity` and
`paper_sim`; the head revert `execution reverted: 45` is recognised as "healthy again".

## Files

`bot.py`, `run.sh`, `executor-runtime.hex` (paper code override, `eth_getCode` of the fork deployment),
`seed-users.json` (1,015 borrowers: every `onBehalfOf` of a Borrow log since the pool's deployment block
24648114, `scratch/trial-xlend-base/seed.py`).

The cover sweep (smaller covers for debts of 2,000 USD or more) is inherited from trial-aave-base's code,
copied, not imported.
