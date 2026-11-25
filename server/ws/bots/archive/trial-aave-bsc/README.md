trial

# trial-aave-bsc

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): Aave v3 liquidations on BNB Smart Chain. Win rate
is measured by sending; nothing here counts as expected revenue under the race rule.

## What it does

1. Waits on the farm feed for `LiquidationCall` on the Aave v3 Pool `0x6807dc923806fe8fd134338eabca509979a7e0cb`
   (topic0 `0xe413a321...5286`). One liquidation usually means a price flip that put other users under water.
2. On an event (and about every 60 s as a safety poll, hourly over the whole universe) reads
   `getUserAccountData` for the near-HF list in one Multicall.
3. For a user with HF < 1 and debt >= 5 USD it simulates the exact executor call for the user's supported pairs
   (debt USDC, USDT or WBNB; collateral BTCB, WBNB, ETH, USDT or USDC), PancakeSwap V3 fee 500 first, covers of
   103%, 50%, 25% of the debt first, and takes the first combination that simulates (speed first: 0.45 s
   blocks); other fee tiers (100, 2500) and smaller covers follow, at most 40 simulations per user.
4. Live: sends `liquidate(...)` on its executor when simulated gross > the signed gas cap. The executor
   flash-borrows the cover from the Aave pool itself (`flashLoanSimple`), calls `liquidationCall`, swaps the
   seized collateral on PancakeSwap V3 (`0x1b81d678...` SwapRouter), repays with the premium, swaps a USDT gain
   to USDC (fee 100) or unwraps a WBNB gain, and reverts unless the pay-token balance grew by `minProfit`
   (= the gas cap). The bot wallet is paid in USDC or native BNB. Paper: logs `paper_sim`.

## Competition, last 7 days (blocks 132801220-134145220, to 2026-11-17)

Data: `scratch/trial-aave-bsc/liq-rows.json` (census), `parent-hf.json`, `tips.json`.

- 127 `LiquidationCall` events, 17 liquidator contracts: `0x5ac9bc14` 37, `0xc4fc3e00` 20 (dust batch),
  `0x0ff94b69` 12, `0x5bebfca2` 11 (dust batch), `0xb3c3f9b1` 9, `0xf000042d` 9, `0xb2eb7ec4` 6, ten others 1-4.
- Debt USDT 76, USDC 49, WBNB 1, FDUSD 1 (out of scope); collateral BTCB 50, WBNB 37, USDT 22, ETH 16, USDC 2.
  91 events have a cover above 5 USD (up to 96,426 USDT); 36 are 0.06-0.3 USD dust sweeps in two batch txs.
- Blocks to take: of the 91, 84 flipped inside the capture block; 7 were under water at the parent block
  (0.45 s before), 4 of those also 2 blocks before, none 4 blocks before.
- Gas price of the winners (91 receipts): min 0.05, median 0.1, p90 1.0, max 26.3 gwei; median cost 8.3e-5 BNB
  (about 0.05 USD). Most takes sit at tx index 2-6 while paying the 0.05 gwei floor, so their position is
  bought outside the gas price (builder bundles), which this bot does not do. 7 takes sit at index 43-152.

This bot bids at most 50% of simulated gross and never signs more than 0.90 USD of gas (about 1.2-1.5 gwei at
0.9-1.2M gas), so it can only win users left under water for a block or more and the takes nobody bundles.

## Loss bound

- Executor reverts unless the gain >= `minProfit`; a lost attempt costs gas only (0.35-0.72M gas for a revert
  on the fork, 0.02-0.06 USD at 0.05-0.1 gwei, at most 0.90 USD at the signed cap).
- `gasPrice x gasLimit` < 0.90 USD per send, gas price <= 3 gwei, gas limit <= 3,000,000.
- Wallet holds gas only (12 USD of BNB). No principal: the cover is an Aave flash loan repaid in the tx.

## Read cost

- Relay: near scan 1440 x 26 CU = 37,440; full scan 3 calls x 24 x 26 = 1,872; discovery 144 x 85 = 12,240;
  about 51,500 CU/day, hard-capped in code at 75,000 CU per UTC day.
- Feed: `/logs/bsc` filter address = Pool, topic0 = LiquidationCall, about 18 events/day, about 6,000 CU/day.
- Total about 58,000 CU/day = 0.03 USD/day at 1M CU = 0.53 USD.
- On feed `gap`, 429, 503 or timeout the bot re-reads the near list through the relay, then waits 30 s.

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (with `executor=`), `discover`, `scan`, `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`,
`paper_sim`, `send`, `send_result` (`result` won/lost, `gas_used`, `send_block`, `winner_block`, `winner_tx`,
`blocks_after_winner`), `signer_reject`, `feed_error`, `read_budget`.

## Fork proof

`scratch/trial-aave-bsc/proof.py` (reset bsc 133299655, deploy, non-owner and NoProfit guards, success A
+12.551827 USDC on a USDC debt, success B +28.956590 USDC on a USDT debt through the exit swap, exhausted);
`scratch/trial-aave-bsc/selftest.py` checks the bot's calldata against `cast calldata` for all three debt
tokens and runs the bot's own `attempt()` pinned to the proof block (two opportunities, 12.55 and 28.96 USD)
and 3 blocks earlier (nothing). The WBNB-debt path (unwrap to native) is the same code as the USDC path plus
`withdraw`; it is checked by calldata only (1 WBNB-debt event in 7 days).

## Files

`bot.py`, `run.sh`, `executor-runtime.hex` (paper code override, `eth_getCode` of the fork deployment),
`seed-users.json` (541 users: 4 days of Borrow logs + users liquidated in 7 d).
