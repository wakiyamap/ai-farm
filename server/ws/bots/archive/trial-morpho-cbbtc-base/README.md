trial: cheap-chain trial bot (decision 2026-11-17-cheap-chain-trials), Morpho Blue cbBTC/USDC liquidations on Base.

# trial-morpho-cbbtc-base

**What it does.** When the BTC/USD feed behind the market's oracle updates, the bot reads the 400
borrowers nearest the liquidation threshold in one Multicall, simulates `TrialMorphoTake.take` for
those at or over it (debt / maxBorrow >= 0.9998), and (live) sends it. The executor calls `Morpho.liquidate(seized=0, repaidShares)`,
sells the seized cbBTC for USDC on the UniV3 0.05% pool inside Morpho's callback, lets Morpho pull the
repayment, and reverts `NoProfit()` unless its USDC balance grew by `minProfit`. No flash loan, no
principal: the wallet holds gas only. Gain goes to the bot wallet as USDC.

## Last 7 days of competition (ledger `morpho_blue.liquidate`, attempts:1472, lead 170)

| | |
|---|---|
| Liquidate events in this market | 4,222 |
| Distinct takers | 84 |
| Largest class | Atlas-routed bundles (0x9cbb82b9..., 0xd12810b1..., 0xed989ee2...): the oracle update and the liquidations are one tx, tip about 15 gwei. Not winnable. |
| Small-ticket takers | 0xc3cb8636..., 0xfd516d09..., 0x3185dba6... (tip 1.25 gwei), 0x5ac9bc14... (0.019 gwei), 0x20f63594... (0.033 gwei) |
| Blocks from takeable to taken | 0 for most (same block as the oracle print); measured 2 blocks (0.4 s) for the fork-proof case: oracle moved in 57583734, borrower 0xd62debfd... taken in 57583736 |
| Priority fee level | median 15 gwei (Atlas), 0.02-3 gwei small takers, base fee 0.005-0.012 gwei |
| Gross per take | 4.384% of repaid at the oracle price; median repaid 5,400 USD in a 16-sample; fork case 27.86 repaid -> +1.2149 USDC |

The bot arrives about 1 s after the update log (feed delivery), i.e. 4-5 Base blocks late. It can win
only what the same-block takers leave. That share is what the trial measures.

## Send condition (bot.py `attempt`)

- simulate the exact calldata with `eth_call`; gross = returned USDC gain;
- priority fee = 25% of gross at most, `maxFeePerGas = min(0.5 gwei, 2 x gasPrice + priority)`;
- gas cap = 450,000 x maxFeePerGas valued at 4,000 USD/ETH + 0.02 USD L1 data fee; must be < 1 USD;
- send only if gross > gas cap; `minProfit` = gas cap, so the executor enforces it too;
- a signer rejection is final; 600 s cooldown per borrower.

Every send logs `send_result` with `result` won/lost, `gas_used`, `gas_cost_wei` (L2 + L1 fee),
`winner_block`, `send_block`, `blocks_after_winner`.

## Reads

- feed: `/logs/base?address=0xe5ec87a39445b8d5b751b116802a53c5ae7e9df1&topic0=<AnswerUpdated>,<0x8d530b9d...>`
  (about 290-400 events/day, about 20k CU/day with the idle cost); on `gap`, a removed log, 429/503 or
  a connection error the near set is re-read through the relay;
- relay: two Multicall `eth_call`s (52 CU, 400 nearest borrowers) per update or per 300 s when quiet
  (about 400/day = 21k CU); a full scan of the 34,815 seeded borrowers (175 calls = 4.6k CU, about 42 s)
  every 6 h, or after a 1% oracle move but at most every 30 min (4-8/day = 18-36k CU). About 40-57k
  CU/day, hard cap 80,000 in code.
- Total about 60,000-77,000 CU/day = 0.03-0.04 USD/day at 1M CU = 0.53 USD.

## Limits known at placement

- Borrower universe is a seed (`seed-borrowers.json`: all 34,815 positions with at least about
  0.9 USDC of debt out of 41,026, Morpho public API 2026-11-16, `scratch/trial-morpho-cbbtc/seed2.py`).
  Borrowers who open after that are not seen; re-seed if the trial is extended.
- Size cap 150,000 USDC repaid per take (pool depth); larger debts are taken in part, with one
  retry at 1/8 size when the simulation fails. Up to 5 candidates per wake, largest debt first.
- A candidate whose simulation fails for a reason other than "position is healthy" is skipped for 6 h.
- Live needs `EXECUTOR_ADDR_BASE` or `EXECUTOR_ADDR`; the bot exits if unset.
- At placement the nearest borrower sits at debt/maxBorrow 0.950: nothing is takeable until BTC falls
  about 5% from 65,290 USD.

## Fork proof

`scratch/trial-morpho-cbbtc/proof.py`, result `proof-result.json` (see manifest `fork_evidence`).
