trial: Silo v1 flash liquidations on Arbitrum. Measures by sending whether a 30 s keeper wins any of the rare, small liquidations in this old lending book; it is not expected to earn.

## Competition, last 30 days (to block 525,581,460)

`scratch/trial-silo1-liq-arbitrum/competition.py` -> `competition.json`. `Liquidate` over all 61 silos: 5 logs in 2 transactions (same-shape `Borrow` control: 104 logs).

| date | block | operator (EOA via executor) | silo | tx index | gas used | fee | taken after insolvency |
|---|---|---|---|---|---|---|---|
| 2026-11-09 | 522,482,164 | 0xfff88151 via 0x10d1b4a5 | 0xea996128 | 1 | 2,478,484 | base fee 0.0207 gwei, tip 0 | 1 block, 1 s |
| 2026-11-14 | 524,033,995 | 0xd9fffdf0 via 0x5ac9bc14 | 0xa1cada48 | 7 | 1,022,667 | base fee 0.0201 gwei + 1 wei | 166 blocks, 42 s |

Only the second is inside the last 7 days: tx `0x05e65899e9ae2fbc48d82a746e2d3f1ab191c28c1919e979f78db81ee56421a1`, seized 0.0010052 WETH, repaid 1.734291 USDC.e. Priority fees: none (Arbitrum is first come first served). The first operator reacts within a block, the second took 42 s; a 30 s sweep can only win cases the fast one skips.

## Mechanism

`Silo.flashLiquidate(address[] users, bytes data)` (no modifier, verified source) on an insolvent borrower:

1. the silo accrues interest, sends the borrower's WHOLE collateral in every asset to the caller (minus the protocol liquidation fee),
2. calls `siloLiquidationCallback(user, assets, receivedCollaterals, amountsToRepay, data)` on the caller,
3. reverts `NotSolvent` unless the borrower is solvent afterwards, i.e. the whole debt was repaid with `repayFor`.

The collateral arrives before the callback, so no flash loan is needed. The executor `Silo1LiqTake.take(silo, user, weth, routes, minProfit)`:

- pre swaps: buy each owed asset with Uniswap V3 `exactOutput` (SwapRouter02) for exactly what is owed, paying with seized collateral;
- `repayFor` the whole debt;
- post swaps: sell what is left of every non-WETH asset to WETH (`exactInput`);
- revert if any non-WETH silo asset remains, or unless WETH grew by `minProfit`; unwrap the gain, require zero WETH left, and pay it to the bot wallet as native ETH.

A solvent borrower makes the silo return without doing anything, so the take reverts `NoProfit(0)`.

## What the bot does

- Seed: `silos.json` (61 silos from the factory 0x4166487056A922D784b073d4d928a516B074b719 `NewSiloCreated` logs) and `borrowers.json` (9,196 silo/borrower pairs that still held debt share tokens at block 525,579,478, out of 46,709 that ever emitted `Borrow`; `scratch/trial-silo1-liq-arbitrum/scan.py`, `prune.py`).
- Once a day: rebuild the watch list = pairs whose debt is worth at least 0.0003 ETH at the silo's own oracle price (269 today). Smaller debts cannot pay for one send.
- Every 2 h: `Borrow` logs since the last scan; new borrowers are watched at once.
- Every 30 s: one Multicall3 `eth_call` with `isSolvent(user)` for every watched pair.
- A newly insolvent pair: build routes (each silo asset against WETH through its deepest Uniswap V3 pool, found with `factory.getPool`). Skip the silo if any asset has no sale route. Otherwise `eth_estimateGas`, simulate, and send only if gain > gasLimit x maxFeePerGas, with `minProfit` = that cap + 1. A case that reverts or stays under the cap is retried once a day.
- Logs (`logs/bot.jsonl`): `start`, `watch_rebuilt`, `insolvent` (when the set changes), `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`, `send_result` (won / lost, gas used, winner block and tx, blocks after the winner), hourly `check`.

## Proof

The fixed artifact passed `python3 scratch/trial-silo1-liq-arbitrum/proof.py 524033994 proof-fix-31c8c821.json`: reset to the paid take's parent block, deploy, fund, guard reversions, success, nothing-left reversion, and release. The success transaction `0x8cb14350d1ba1f45fabcfc7f448f1956abfc5cf934eecc0304207e60dd7b01b4` raised the owner's native balance by 5,857,352,253,371 wei after fork gas. It used 894,758 gas at 0.1 gwei; gross payout was 95,333,152,253,371 wei. The high-minProfit guard `0xc5d6d05717f4c3460c4e8eace2bcad2967a676f30e8868032f03d4a34d0b5dbc` reverted. After success, executor native, WETH, USDC.e and third silo asset balances were zero, and their router and silo allowances were zero. The borrower was solvent. Full hashes and receipts are in `scratch/trial-silo1-liq-arbitrum/proof-fix-31c8c821.json`.

Proven by archive `eth_call` with the executor as a code override, running this bot's own functions (`scratch/trial-silo1-liq-arbitrum/selftest.py` -> `selftest-result.json`), at the parent block of the 2026-11-14 take:

| check | result |
|---|---|
| watch list + insolvency sweep | finds borrower 0xc9f2ecb6 |
| `eth_estimateGas` | 1,056,449 (signed limit 1,373,383) |
| gain | 95,337,875,566,261 wei (0.17 USD) vs signed cap 41,275,654,055,383 wei: would send |
| non-owner | revert `NotOwner` |
| borrower with no position | revert `NoProfit(0)` |
| minProfit = 2 x gain + 1 | revert `NoProfit(gain)` |
| same call at the take block and at head | revert `NoProfit(0)` |
| calldata encoder vs `cast calldata` | identical |

Head dry run of the main loop (`dryrun.py` -> `dryrun-result.json`): 269 watched, 15 insolvent, all 15 revert in simulation, so nothing is sent. All 15 are in silo 0x7cc5267e (asset PT-weETH-25APR2024, an expired Pendle PT): WETH collateral against PT debt of more than twice its amount (e.g. 0.2426 WETH against 0.5604 PT; `cb_amounts.py` -> `cb-amounts.json`), i.e. bad debt, and the PT/WETH V3 pool is empty. Not a leftover to take.

## Limits

- Routes are Uniswap V3 only. A silo with any asset lacking a WETH sale route is skipped. The executor also reverts if any silo asset remains after the sale.
- A borrower whose collateral is split over two assets, neither of which covers the debt alone, reverts in the pre swap.
- Debt share tokens moved without a `Borrow` event are not seen until the borrower borrows again.

## Read cost

Sweep 2,880 x 26 CU = 74,880; new-borrower logs 12 x 235 = 2,820; daily watch rebuild 3,276 (measured); daily retries about 500. About 81,500 relay CU per day = 0.043 USD per day at 0.53 USD per 1M CU. Code cap 95,000 CU per day.

## Loss bound

One send costs at most gasLimit x maxFeePerGas: at most 3,000,000 gas x 0.05 gwei = 0.00015 ETH (0.27 USD at 1,800 USD per ETH); typical 0.00004 ETH (0.07 USD). Capital 10 USD of ETH on Arbitrum, no principal.
