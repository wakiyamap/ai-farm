trial — cheap-chain trial bot (decision 2026-11-17-cheap-chain-trials): measures the farm's win rate on Curve LlamaLend liquidations on Arbitrum by sending, capital 10 USD, at most 1 USD per send.

# trial-llamalend-arbitrum

One market: the LlamaLend WBTC / crvUSD controller `0xb9adddcf4e01c2f64f8f2cd9a050dc35585ea053` (factory `0xcaec110c784c9df37240a8ce096d352a75922dea`, 25 markets; this is the one with a 7-day take whose route is fork-proven).

## What it does

1. Every 75 s: one Multicall3 `eth_call` reads `health(user, true)` for every open loan (24-25 loans; list refreshed every 30 min from `n_loans()` / `loans(i)`). This is the value `liquidate()` itself tests.
2. While any borrower is within 0.05% of zero health it polls every 3 s instead (at most 1,400 fast polls per UTC day).
3. For a borrower under zero it simulates the executor call for four flash sizes (0.0017, 0.003, 0.01, 0.05 WETH), takes the best, estimates gas, and sends only if the simulated gross is above the signed gas cap (`maxFeePerGas x gasLimit`, itself at most 50% of the gross and at most 0.80 USD priced at 4,000 USD/ETH). `minProfit` on-chain = the gas cap + 1 wei.
4. The executor `LlamaTake.take(Job)` does everything in one transaction: Balancer V2 flash loan of WETH, WETH -> ARB (UniV3 0.05%), ARB -> crvUSD (Curve tricrypto `0x845c8bc9...`), `controller.liquidate(user, 0)`, seized WBTC -> WETH (UniV3 0.05%), leftover crvUSD and ARB back to WETH, repay, revert `NoProfit()` unless the WETH gain is at least `minProfit`, unwrap and pay the bot wallet in ETH.

`BOT_MODE=paper` simulates with a code override (`executor-runtime.hex`) and sends nothing. `BOT_MODE=live` needs `EXECUTOR_ADDR_ARBITRUM` (or `EXECUTOR_ADDR`) and sends through the signer.

## Competition, last 7 days (blocks 523,330,166-525,374,422)

2 `Liquidate` events on all 25 LlamaLend controllers on Arbitrum.

| tx | block | taker | takeable -> taken | gross | gas | priority fee |
|---|---|---|---|---|---|---|
| `0x33b7fc9e63d46bcfef8e232c06d0ff39d83bbbf435022960a51361d0d9da750e` | 524327722 | `0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd` | health under zero at 524327720: 2 blocks, same second (`scratch/trial-llamalend-arbitrum/window.json`) | 0.861 crvUSD | 1,518,327 gas at 0.02027 gwei = 0.053 USD | none |
| `0x9a4113c2efb52155abbf4e3a332c41d5730a20deae26aa8c47b6241b4744dd29` | 523741610 (tx index 2) | `0x8ab5db84d241f4cca7de44d9f84d393f78b099f1` | 0 blocks: a direct liquidate at the parent block reverts "Not enough rekt" | about 4.8 USD | 775,501 gas at 0.02016 gwei = 0.027 USD | none |

Both takers react in under a second and pay no priority fee. A timer bot does not beat that: this trial wins only what they skip or are late for. Expect few or no sends; the result of the trial is that number.

Known at start (2026-11-18 18:45Z): borrower `0x2b7dd66f1c31f7d3c785bd6414512b70bf923a73` is under zero but is bad debt (AMM holds 1.54 crvUSD and no WBTC against 2.09 crvUSD of debt); every flash size reverts in simulation, so the bot logs `simulate_revert` for it and backs off to one re-check per hour. Nearest healthy borrower: 6.3% above zero.

## Fork proof

`python3 scratch/trial-llamalend-arbitrum/proof.py` (results `proof-result.json`): reset to 524327721, deploy, then non-owner revert, `NoProfit()` guard revert, success +0.000495 ETH gross (0.86 USD at 1,736 USD/ETH; gas 1,625,593), repeat reverts "Loan doesn't exist". Hashes are in `manifest.yaml`. `harness.py` runs the bot's own scan and attempt path at that block and at head.

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (with `executor=`), `loans`, `scan` (loans, unhealthy, min_positive_health, near, fast_used; at most one per 75 s plus one per near/far change), `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim` (paper), `send` and `send_result` (live: `result` won or lost, `gas_used`, `gas_cost_wei`, `paid_wei`, `net_wei`, `block`, `winner_block`, `blocks_after_winner`), `signer_reject`, `scan_error`, `read_budget`.

## Read cost

| read | per day | CU |
|---|---|---|
| health Multicall every 75 s (`eth_call`, 26 CU) | 1,152 | 29,952 |
| loan list every 30 min (2 x `eth_call`) | 96 | 2,496 |
| bad-debt borrower re-check, hourly (4 x `eth_call`) | 96 | 2,496 |
| fast poll while near, 3 s (`eth_call`), capped | up to 1,400 | up to 36,400 |

About 35,000 CU/day idle, at most about 71,400 = 0.019 to 0.038 USD/day at 0.53 USD per 1M CU. No feed filter. The code stops reading at 90,000 CU per UTC day (`state/cu.json`).

## Limits

- One controller, one route. The other 24 markets need their own collateral paths (all are call arguments of the executor; only `bot.py` constants would change).
- The Curve leg is fixed to coin indices 1 -> 0 (ARB -> crvUSD) in the executor.
- Worst case per send: `maxFeePerGas x gasLimit`, under 0.35 USD at today's ETH price (0.80 USD at the 4,000 USD/ETH the code assumes).
