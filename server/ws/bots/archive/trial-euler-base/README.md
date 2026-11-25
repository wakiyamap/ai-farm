trial

# trial-euler-base

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): Euler EVK liquidations on Base, USDC debt
with WETH or cbBTC collateral. Win rate is measured by sending; nothing here counts as expected revenue
under the race rule.

## What it does

1. Waits on the farm feed for `AnswerUpdated(int256,uint256,uint256)` (topic0 `0x0559884f...fc5f`) on the
   Chainlink WETH/USD aggregator `0x05c84a58fe042275b37db038baacd15f410c7bb0` (behind feed proxy
   `0x71041ddd...`, which the oracle routers of all three debt vaults resolve WETH to;
   `scratch/trial-euler-base/probe.json`). A price step is what makes a position pay.
2. On an event (and about every 110 s as a safety poll, hourly over the whole universe) reads
   `accountLiquidity(account, true)` on the debt vault for the near-health list in one Multicall.
3. For an account with collateral value < liability and debt >= 5 USD: `EVC.getCollaterals(account)`, keeps
   the collateral vaults whose asset is WETH or cbBTC, reads `checkLiquidation(executor, account, collateral)`
   and simulates the exact executor call (repay = max repay, capped at 50,000 USDC; from 2,000 USDC also
   1/2, 1/4, 1/8 of it) and keeps the best.
4. Live: sends `run(Params)` on its executor when simulated gross > the signed gas cap. The executor
   flash-borrows the USDC from Morpho, runs one EVC batch (liquidate, repay, redeem, disableController),
   sells the collateral asset on the UniV3 0.05% pool against USDC, repays, and reverts unless its USDC
   balance grew by `minProfit` (= the gas cap). All USDC goes to the bot wallet. Paper: logs `paper_sim`.

Debt vaults: eUSDC-1 `0x0a1a3b5f2041f33522c4efc754a7d096f880ee16`, eUSDC-102
`0xeef57677c2fc1a930eed234e3545e750c88f6743`, eUSDC-91 `0x91a9ed5d4368499b1fe41f721ab13e64760b3f05`.
Borrowers come from `Borrow` logs: `seed-accounts.json` (what the public node served on 2026-11-17 plus the
violators of the last 7 days), new ones every 10 min, and a one-time backfill of 45 days by the bot itself.
Accounts whose only collateral is something else (ZRO, AERO, PT tokens, nested vault shares) are skipped.

## Competition, last 7 days (to 2026-11-17, attempts:1846, `scratch/trial-euler-base/events7d.json`)

- 18 `Liquidate` events on the 41 largest Base EVK vaults, by 5 liquidator contracts: `0x5ac9bc14` 9,
  `0xfb710775` 3, `0x59b043a4` 2, `0xb091bc76` 2, `0xecf4e632` 2.
- 8 have USDC debt (repaid 14 / 20 / 21 / 43 / 181 / 427 / 475 / 1,300 USDC); 6 of them are in this bot's
  scope (5 WETH collateral, 1 cbBTC), all taken by `0x5ac9bc14` (5) and `0xecf4e632` (1). The rest of the 18
  is AERO-debt dust (8), one cbBTC-debt and one VVV-debt case.
- Blocks to take (`takeable.json`, `checkLiquidation` at N-k): the accounts were liquidatable for 3 to 50+
  blocks before the take, but only at a small discount; the seizable amount stepped up 1.9% two to four
  blocks (0.4-0.8 s) before the take, i.e. the incumbent follows the price update that makes it pay by
  2-4 blocks. The farm's feed delivers a log about 1 s after its block, so this bot is expected to arrive
  later than that and to win only what the incumbents leave.
- Fees paid by the winners: effective gas price 0.006-1.12 gwei (1.12 gwei on the 1,300 USDC take, 0.02-0.03
  gwei on the 20-43 USDC takes), gasUsed 658k-1.16M, tx index 2-235, total fee 0.008-1.45 USD.
- This bot on the same cases at the parent block (`harness.out`): +23.17 USDC (1,300 take), +0.48, +0.39,
  +0.40, +0.33 (cbBTC), and a skip (0.06 gross under the gas cap) on the 14 USDC take.

This bot bids at most 50% of simulated gross and never signs more than 0.90 USD of gas.

## Loss bound

- Executor reverts `NoProfit` unless the USDC gain >= `minProfit`; a lost attempt costs gas only (about
  375k-465k gas when the position is already gone, 745k-950k when it runs to the guard).
- `maxFeePerGas x gasLimit + 0.02 USD L1 allowance < 0.90 USD`, never above 0.5 gwei; send only when
  simulated gross > that cap; on-chain `minProfit` = the cap.
- No principal: the repayment is a Morpho flash loan. The wallet holds gas only (15 USD, under Base's 18 USD cap).

## Read cost

- Relay: near scan about 785/day on the timer plus one per price event (about 350/day: 41 `AnswerUpdated`
  in the last 2.8 h) = about 1,135 x 26 CU = 29,500; discovery 144 x 70 = 10,080; full scan 24 x 26 x 1-2
  = about 1,000; about 41,000 CU/day. One-time backfill: about 390 pages x 60 = 23,400 CU on the first day.
- Feed: about 350 events/day x about 35 CU + idle long-polls about 5,800 = about 18,000 CU/day.
- Total about 59,000 CU/day = 0.03 USD/day at 0.53 USD per 1M CU (about 82,000 on the first day). The code
  stops relay reads at 75,000 CU per UTC day.

## Logs (`logs/bot.jsonl`)

`start` (with `executor=`), `scan`, `discover`, `backfill`, `feed`, `opportunity`, `opportunity_skip`,
`simulate_revert`, `paper_sim`, and in live `send`, `send_result` (won or lost, gas used, the winner's block,
tx and tx index, blocks after the winner), `signer_reject`.

## Checks

- `scratch/trial-euler-base/proof.py`: fork proof (success, guard, non-owner, nothing left) on the WETH case;
  `proof.py cbbtc` the same on the cbBTC case. The cbBTC run found that a flash loan equal to the debt taken
  over can be one unit short (`E_TransferFromFailed`); the executor borrows 0.1% + 10 units more.
- `scratch/trial-euler-base/harness.py`: bot calldata equals `cast calldata`; the bot's own scan and attempt
  path replayed at the parent block of the six in-scope historical takes.
