trial (cheap-chain trial, decision 2026-11-17-cheap-chain-trials): Fluid VaultT1 liquidations on Polygon, WBTC/USDT0 vault.

# trial-fluid-polygon

Fluid's vault `liquidate(debtAmt, colPerUnitDebt, to, absorb)` is open to anyone: the caller repays
any part of the debt that sits above the liquidation threshold and receives collateral at the
oracle price plus the vault's penalty. The bot repays with a UniV3 flash swap and keeps the
difference as native USDC, all in one transaction through its executor (`TrialFluidTakeUsd`).
Scope: vault 0xdf16adaf80584b2723f3ba1eb7a601338ba18c4e (WBTC collateral, USDT0 debt), which had
72 of the 90 Polygon takes of the last 7 days.

## Last 7 days of competition (attempts:2246, attempts:2133; window 2026-11-11 to 11-18 19:44 UTC)

- `LogLiquidate(address,uint256,uint256,address)` (topic0 0x80fd9cc6...), blocks 96,644,000-97,550,672:
  **90 takes, 8 liquidator contracts**, all between block 97,191,872 and 97,334,454
  (2026-11-12 14:21 to 11-15 01:45 UTC, the falling-price days); none since. Top takers:
  0xf000042d2b48921c (52), 0x5ac9bc14376bf272 (15), 0xa0000470c3e42e9e (8).
- Blocks from takeable to taken (71 takes probed at archive blocks, `scratch/trial-fluid-polygon/windows.json`):
  66 land in the block in which the debt becomes takeable; 5 were takeable one block earlier
  (4 of those were then taken at tx index 0-2 with an 11,350-88,396 gwei priority fee, one,
  block 97,322,803, at tx index 295 with an ordinary 133 gwei); none waited 2 blocks.
  A 40 s timer bot therefore sees almost nothing: that is what the trial measures.
- Winner fees: priority fee median 121 gwei (usual range 73-177) on a base fee of about 250 gwei;
  tx index anywhere from 0 to 867.
- One attempt: about 0.5M gas used (fork: 480,942 and 533,821) x about 350 gwei = 0.19 POL = 0.015 USD
  at POL 0.080 USD; observed median take cost 0.029 USD.
- Gross: sample median 18.25 USD, max 80.91 USD (tx 0x5c3cdd0a...). Fork, same state as two mainnet
  takes: +24.15 USDC on 455.15 USDT0 repaid and +22.44 USDC on 414.83 USDT0, about 5.3% of the debt.

## How it runs

- Every 40 s: one Multicall3 `eth_call` with the vault probe and `slot0()` of the WPOL/USDC pool
  (POL price for the gas cap). No feed filter.
- At least 1 USDT0 to take: simulate `take` (minProfit 1), `eth_estimateGas` x 1.30, fee cap so that
  gasLimit x maxFeePerGas < 0.40 USD (POL valued 15% above the pool price), priority bid at most 40%
  of the simulated gross (at least 30 gwei), send only if gross > that send's gas cap, and pass the
  gas cap in USDC as `minProfit` (the executor reverts below it). After a lost send: 2 min pause.
- Route (all call arguments): flash USDT0 from UniV3 USDC/USDT0 0.01% 0x31083a78..., liquidate,
  sell WBTC on UniV3 WBTC/USDC 0.05% 0x32fae204..., pay the first pool in USDC. At most 3,000 USDT0 per take.
- `BOT_MODE=paper`: same path with an `eth_call` code override of the fork deployment, sends nothing.
  `BOT_MODE=live`: `EXECUTOR_ADDR_POLYGON` / `EXECUTOR_ADDR` required; sends through the signer.
- Logs (`logs/bot.jsonl`): `start`, `scan` (every poll that sees debt, heartbeat every 10 min),
  `simulate_revert`, `opportunity_skip`, `opportunity`, `paper_sim`, `send_result` (won/lost, gas
  used, winner block, blocks after winner), `signer_reject`, `read_budget`, `loop_error`.

## Read cost

2,160 polls/day x 1 eth_call x 26 CU = 56,160 CU/day (0.030 USD at 1M CU = 0.53 USD), plus about
100 CU per opportunity (2 simulations, estimate, gas price) and up to 700 CU per send (receipts, logs).
Hard cap in code: 90,000 CU/day (`CU_CAP`).

## Limits known at placement

- Timer, not an oracle feed: a take that appears and is gone inside 40 s is never seen.
- A lost send costs gas at the bid: at most 0.40 USD, typically about 0.25 USD (a revert uses 0.34-0.58M gas).
- The vault pays collateral at its oracle price; when the pool price gives no margin the
  simulation reverts `NoProfit` and nothing is sent (2 min cooldown).
- Not covered: wstETH/USDC 0xa0f83fc5 and WBTC/USDC 0xf55b8e9f (USDC debt needs another profit
  token, and UniV3 Polygon has no usable wstETH pool against USDC or WPOL; 4 of 90 takes), and the
  non-T1 vault 0xf2c8f544 (14 of 90).
- Self check: `scratch/trial-fluid-polygon/selftest.py` runs this bot's read and attempt path on the
  fork at block 97,322,802 (opportunity + paper_sim success, 24.145917 USDC) and at the relay head.
