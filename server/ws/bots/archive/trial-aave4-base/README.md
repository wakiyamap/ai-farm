# trial-aave4-base

**trial** (cheap-chain trial, decision `2026-11-17-cheap-chain-trials.md`): the win rate is measured by sending, not by counting past windows. Capital 18 USD, no top-up, every send capped under 1 USD of gas.

## What it does

Aave V4 on Base has one spoke, `0x17905db0e4a3514467539956c084180616ae7b8d` (hub `0xa4d5947e...`, "Equities Hub"): 8 Coinbase tokenized equities (AAPLc, AMZNc, GOOGLc, METAc, MSFTc, NVDAc, TSLAc, SPCXc; 8 decimals) are the collateral and USDC (reserve 7) is the only borrowed asset (7.45M USDC at placement, 329 debtors). Anyone may call `liquidationCall(collateralReserveId, debtReserveId, user, debtToCover, receiveShares)` on a user whose health factor is under 1 and receives the collateral at a bonus of about 5% (minus 10% of the bonus as protocol fee).

The bot waits on the farm feed for `AnswerUpdated` on the 8 stock price aggregators, reads `getUserAccountData` for the borrowers under health factor 1.15 in one Multicall, and for each one under 1 simulates the executor call:

1. Morpho Blue flash loan of USDC (zero fee), a little more than the user's debt;
2. `liquidationCall` on the spoke (it restores only what the target health factor allows);
3. the seized stock token is sold to USDC on a UniV3 pool (the pool is a call argument; the bot simulates each known pool and keeps the best);
4. Morpho takes the loan back; the executor reverts `NoProfit()` unless its USDC grew by `minProfit`, then pays everything to the bot wallet.

It sends only when the simulated gross is above that send's gas cap, and passes the cap as `minProfit`.

## Competition, last 7 days (lead 42 scout, blocks to 58362485, `scratch/v4-7d-rows.json`)

| | |
|---|---|
| paid entries | 8 `LiquidationCall`, all USDC debt; collateral NVDAc 6, AMZNc 1, SPCXc 1 |
| takers | 4 addresses: `0x5ac9bc14...` 5, `0x03a6793b...`, `0xf000042d...`, `0x8407699e...` 1 each |
| gross per capture | median 1.46 USD, max 14.28, sum 42.38 (bonus 4.95-6.24% of debt) |
| blocks from takeable to taken | 2/8 in the first liquidatable block; 5/8 after 1-7 blocks (0.2-1.4 s); 1/8 dust (0.46 USD debt) after 128+ blocks |
| winners' priority fee | median 0.054 gwei, max 0.50 gwei; total gas paid median 0.059 USD, max 0.75 |
| one attempt | 530k gas (fork) = 0.005 USD at the 0.005 gwei base fee |

The feed delivers a log about 1 s after its block, so the bot is expected to lose most 1-7 block cases; the trial measures how many it wins. Every send logs `send_result` with `won`/`lost`, gas used, the winner's block and `blocks_after_winner`.

## Loss guard

- Executor: `take()` reverts unless the USDC balance grows by `minProfit` (> 0). Worst case of a send is its gas.
- `GAS_LIMIT` 800,000 x `MAX_FEE_WEI` 0.25 gwei = 2.0e-4 ETH: 0.36 USD at ETH 1,820, and under 1 USD even valued at 4,000 USD/ETH plus the 0.02 USD L1 data-fee allowance. The bot refuses to send if that cap would reach 1 USD.
- Priority fee: at most 25% of simulated gross, never above the fee cap.
- Flash size capped at 50,000 USDC per take.

## Read cost

About 41,000 CU/day = 0.022 USD/day at 1M CU = 0.53 USD.

- Feed filter: `/logs/base`, 8 aggregator addresses, topic0 `AnswerUpdated` `0x0559884f...`: about 440 logs/day x 35 CU + 4 CU/min for the subscription = about 21k CU.
- Relay: one Multicall `eth_call` (26 CU) per update batch (at most 440/day = 11.4k), a 300 s safety poll when quiet (at most 288 x 26 = 7.5k), a full scan of every borrower every 6 h (6 Multicalls + `eth_blockNumber` + one `eth_getLogs` for new `Borrow` logs = 241 CU). Hard cap 80,000 relay CU/day in code (`read_budget` row when hit).
- On `gap`, a removed log, HTTP 429/503 or a connection error the bot re-reads the near set through the relay.

## Files

- `bot.py`: one loop for paper and live. Live needs `EXECUTOR_ADDR_BASE` or `EXECUTOR_ADDR` and exits without it.
- `executor-runtime.hex`: `eth_getCode` of the fork deployment, used as the code override in paper simulation.
- `seed-borrowers.json`: 533 borrowers from the spoke's `Borrow` logs, blocks 51478830-58446811; the bot adds new ones itself.
- Executor source and proof: `scratch/trial-aave4-base/contracts`, `scratch/trial-aave4-base/proof.py`, `selftest.py`.

## Known limits

- The pool table in `bot.py` (`RESERVES`) is static; TSLAc has no liquid pool today, so a TSLAc-only position will fail simulation and be skipped.
- Only USDC debt (the spoke's only borrowed reserve today).
