trial: Metronome Synth liquidations on Base (`Pool.liquidate`, 10% of the repaid synth goes to the caller), taken in one transaction with a free Morpho Blue WETH flash loan. Measures the farm's win rate by sending.

## Mechanism

Metronome Synth v2 Pool `0xc614136d6c5ab85bc2acf0ec2652351642d7f54e` lets anyone call `liquidate(synth, account, amountToRepay, depositToken)` on an unhealthy position: the caller's synth is burned and the caller receives deposit tokens worth the repaid amount plus 10% (FeeProvider.liquidationFees). Debt is in msUSD (5,646) and msETH (166.35 msETH); the whole book is 301k USD over 360 debtors, and 16 positions with about 166k USD of debt sit within 9% of their limit (census 2026-11-19 03:50Z, `scratch/metro/debtors.py`).

One executor call (`MetroLiq.liquidate`, every address is a call argument):

1. Morpho Blue `flashLoan(WETH)`.
2. Buy msETH with WETH on the Slipstream WETH/msETH pool `0x74f72788...` (exact output, 1% over the need). msETH trades about 13% under WETH there, and Metronome values it at its oracle price, which adds to the 10%.
3. If the debt is msUSD: `Pool.swap(msETH, msUSD)` inside Metronome.
4. `Pool.liquidate`, then `depositToken.withdraw`, then the Vesper vault `withdraw` when the collateral is a vault share.
5. Sell the collateral for WETH on a Uniswap V3 pool (none when it is already WETH); swap leftover synth back.
6. Repay Morpho; revert `NoProfit` unless the WETH gained is at least `minProfit`; unwrap the gain and pay it to the bot wallet as native ETH.

## Competition, last 7 days (blocks 56,310,092-59,346,968) and before

- 3 liquidation transactions, 12 `PositionLiquidated` events: liquidator contract `0x27cda76c66107b8ebc094d622fcb149cb26da477` (EOA `0xc0ffeef6...`), 1 event, 5.018 msUSD repaid, paid 3.285e14 wei = 0.58 USD for 1,394,898 gas (tx `0x95912733...`, block 56,748,807, tx index 68); liquidator contract `0xc1a7804726bcf18faa4ee05aed45762a3d992176` (EOAs `0xd54203b2...`, `0xca23d828...`), 11 dust events in 2 txs (0.26 msUSD and 10 x about 0.013 msUSD, tx index 12 and 9).
- Blocks from takeable to taken (`scratch/trial-metronome-liq-base/windows.py` -> `windows.json`, binary search of `debtPositionOf` at past blocks): 5.0 msUSD case 1 block (1 s); 10.0 msUSD case 10 days ago 222 blocks (44 s); the dust cases (0.03-0.5 msUSD) waited 18 days. Over the last 16 days: 8 transactions, 5 liquidator contracts.
- Priority fee of the takers: 100,000-4,373,930 wei per gas (0.0001-0.0044 gwei) on a base fee of 5.0e6-1.55e7 wei. This bot offers up to 30% of its simulated gain (at the 5 msUSD case: 5.2e7 wei per gas).
- Large cases happen in bursts: 50 days ago 12 liquidations of 1,200-18,826 msUSD each (tx index 39-2767, liquidator `0xdeadb043...`), 59 days ago one position was bitten in halves from 4,249 to 7 msUSD over 269 blocks, 47 days ago 8,498 msUSD (`scratch/metro/liqs.py` -> `liqs-rows.json`). In the last 30 days nothing above 10 msUSD.
- What this bot can win: cases that stay open longer than its timer (40 s, 10 s near the limit). It will lose the 1-second ones.

## Bot

- Census at start and every 6 h: all debtors from the two debt tokens' mint logs (one `eth_getLogs`), kept when debt >= 1 USD (109 accounts at the first paper census, 2026-11-19 03:59Z).
- Every 40 s: one Multicall3 `eth_call` with `Pool.debtPositionOf` of every tracked account. 10 s instead while a position is unhealthy or a position with debt >= 20 USD is within 0.05% of its limit (at most 1,300 fast polls a day).
- Unhealthy position with collateral left: `quoteLiquidateMax` for each synth x deposit token, then the executor is simulated (`eth_call`, it returns the gain) for sizes 100% / 99% / 50% / 20% / 5% of the maximum and each exit pool; the best gain wins.
- Send rule: gas limit = `eth_estimateGas` x 1.15; maxFeePerGas = base fee x 1.05 + tip, tip = 30% of the gain spread over the gas limit, cut so that gasLimit x maxFee + L1 allowance stays under 0.90 USD at 4,000 USD/ETH; sends only when gain > that cap, with `minProfit = cap + 1`, after simulating the exact guarded call at the signed gas limit.
- A lost attempt burns most of the route's gas at the bid fee: 0.02 USD at the minimum tip, at most 0.90 USD. At most 6 lost sends per account per hour.
- Logs (`logs/bot.jsonl`): `census`, `check`, `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`, `send`, `send_result` (won / lost, gas used, tx index, winner block and tx).

## Read cost

Base timer 2,160 polls x 26 CU = 56k CU/day; fast mode at most 1,300 x 26 = 34k; census 4 x about 300 CU; an opportunity about 600 CU. Code cap 95,000 relay CU/day = 0.05 USD/day at 0.53 USD per million CU. No feed filter.

## Evidence

`scratch/trial-metronome-liq-base/`: `proof.py` + `proof-msusd.json`, `proof-mseth.json` (fork: guard revert, non-owner revert, success, repeat revert), `selftest.py` + `selftest.json` (this bot's `positions()` and `try_account()` on the fork at the parent block of two real liquidations, calldata against `cast calldata`), `windows.py`, `pools.py`; `scratch/metro/`: `book.py`, `debtors.py`, `liqs.py`, winner traces `scratch/metro-trace.json`, `trace-mseth.json`.
