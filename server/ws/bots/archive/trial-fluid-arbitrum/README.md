trial (cheap-chain trial, decision 2026-11-17-cheap-chain-trials): Fluid VaultT1 liquidations on Arbitrum.

# trial-fluid-arbitrum

Fluid's vault `liquidate(debtAmt, colPerUnitDebt, to, absorb)` is open to anyone: the caller repays
any part of the debt that sits above the liquidation threshold and receives collateral at the
oracle price plus the vault's penalty. The bot repays with a UniV3 flash swap and keeps the
difference as native ETH, all in one transaction through its executor (`TrialFluidTake`).

## Last 7 days of competition (run e7c8bcca, 2026-11-18)

- `LogLiquidate(address,uint256,uint256,address)` (topic0 0x80fd9cc6...), topic-only getLogs, blocks
  522,808,642-525,208,642: **477 takes on 10 vaults, 12+ liquidator contracts**; 429 on the six
  T1 vaults this bot covers (WBTC/USDC 93, WBTC/USDT 90, ARB/USDC 83, ETH/USDC 74, ETH/USDT 67,
  wstETH/USDC 22). Top takers: 0x5ac9bc14 150, 0xb9aea51c 98, 0xb411c70c 85, 0x48daab9f 67,
  0x63b701c7 27. Last take: block 524,328,209 (2026-11-15); none since (prices rose).
- Blocks from takeable to taken, sample of 36 spread over the window (`scratch/trial-fluid-arb/probe.out`;
  "takeable" = `liquidate(1e30,0,0xdead,false)` at an earlier block already returns at least half the
  debt that was taken): 13 became takeable in the block they were taken; 18 were takeable 1 block
  (about 0.25 s) before; 3 for 4 blocks, 1 for 12, 1 for 40 (all five on the ARB/USDC vault, debts
  under 1 USDC). So nearly everything goes within one or two blocks; with a 40 s timer this bot
  only gets what the others leave. That is what the trial measures.
- Winner fees: effective gas price median 0.038 gwei (range 0.020-0.140, one at 1.547);
  0xb9aea51c bids a flat 0.038 gwei priority, others 0-0.12 gwei. Tx index median 6 (range 1-76).
- One attempt: gas used median about 542,000 (400,559-913,999) x 0.038 gwei = 2.1e-5 ETH = 0.037 USD
  at ETH 1,801 USD (WETH/USDC pool price at head).
- Gross (fork, same state as the mainnet takes): +0.000380 ETH (0.68 USD) on 21.91 USDC repaid
  (WBTC/USDC), +0.0000906 ETH (0.16 USD) on 21.57 USDC (ETH/USDC), +0.01036 ETH (18.66 USD) on
  618.88 USDT (WBTC/USDT). Gross is above one attempt's gas in all three.

## How it runs

- Every 40 s: one Multicall3 `eth_call` with the six probes and `slot0()` of the WETH/USDC pool
  (ETH price for the gas cap). No feed filter.
- A vault with at least 1 USDC/USDT to take: simulate `take` (minProfit 1), `eth_estimateGas` x 1.30,
  fee cap so that gasLimit x maxFeePerGas < 0.95 USD (ETH valued 15% above the pool price),
  priority bid at most 40% of the simulated gross, send only if gross > that send's gas cap, and
  pass the gas cap as `minProfit` (the executor reverts below it).
- `BOT_MODE=paper`: same path with an `eth_call` code override of the fork deployment, sends nothing.
  `BOT_MODE=live`: `EXECUTOR_ADDR_ARBITRUM` / `EXECUTOR_ADDR` required; sends through the signer.
- Logs (`logs/bot.jsonl`): `start`, `scan` (every poll that sees debt, heartbeat every 10 min),
  `simulate_revert`, `opportunity_skip`, `opportunity`, `paper_sim`, `send_result` (won/lost, gas
  used, winner block, blocks after winner), `signer_reject`, `read_budget`, `loop_error`.

## Read cost

2,160 polls/day x 1 eth_call x 26 CU = 56,160 CU/day (0.030 USD at 1M CU = 0.53 USD), plus about
100 CU per opportunity (2 simulations, estimate, gas price) and 115 CU per send (receipt, logs).
Hard cap in code: 90,000 CU/day (`CU_CAP`).

## Limits known at placement

- Timer, not an oracle feed: a take that appears and is gone inside 40 s is never seen.
- The vault pays collateral at its oracle price; when the pool price gives no margin the
  simulation reverts `NoProfit` and nothing is sent (2 min cooldown per vault).
- Smart-collateral / smart-debt vaults (T2-T4, 48 of the 477 takes) are not covered.
- The fork reports about 1 gwei gas; `scratch/trial-fluid-arb/selftest.py` substitutes 0.02 gwei
  to exercise the send branch decision (set `SELFTEST_MAINNET_GAS=0` to see the fee-cap skip).
