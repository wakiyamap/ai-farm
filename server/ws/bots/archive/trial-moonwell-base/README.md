trial

# trial-moonwell-base

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): Moonwell (Base) liquidations of mUSDC debt.
Win rate is measured by sending; nothing here counts as expected revenue under the race rule.

## What it does

1. Waits on the farm feed for `LiquidateBorrow` on mUSDC `0xedc817a28e8b93b03976fbd4a3ddbc9f7d176c22`
   (topic0 `0x298637f6...bb52`). One liquidation usually means a price move that put other borrowers under water.
2. On an event (and every 10 min over all known mUSDC borrowers, every ~5 min over the near list) reads
   `Comptroller.getAccountLiquidity` and `mUSDC.borrowBalanceStored` in one Multicall per 100 accounts.
3. For an account with a shortfall and >= 5 USDC of debt it reads `getAssetsIn` and the account snapshots,
   values the supported collateral at the Moonwell oracle, sizes the repay (close factor 0.5, seize must fit
   in the collateral) and simulates the exact executor call.
4. Live: sends `liquidate(...)` on its executor when simulated gross > the signed gas cap. The executor
   flash-borrows USDC from Morpho, calls `mUSDC.liquidateBorrow`, redeems the seized mTokens, swaps the
   collateral on UniV3, repays, and reverts unless its USDC balance grew by `minProfit` (= the gas cap).
   Paper: logs `paper_sim`.

## Competition, last 7 days (attempts:1467 scout, attempts:1682 this build)

- 492 `LiquidateBorrow` events in 412 txs by 67 sender EOAs on the 17 core markets; 381 events on mUSDC
  (286,520 USDC repaid, median repay 3.69 USDC, max 43,440).
- Senders: `0xd9fffdf0` 109 events / 85 txs, `0x8aab7aa0` 32 / 1, `0x143dd73b` 19, `0x609c8738` 16 / 1,
  `0x11f7af68` 15 / 12, 57 more. Each winner calls its own executor; no shared entry point.
- Blocks to take: of 9 recent mUSDC captures above 20 USDC, 5 flipped inside the capture block and 4 were
  already short at the parent block and 300 blocks (60 s) earlier. Class-wide, 237 of 492 events re-liquidated
  an account that was already liquidatable (51 within 16 blocks = 3.2 s; median gap 23,280 blocks).
- Priority fees: 0.0009-64 gwei (median 2.09 gwei in a 20-tx sample), scaling with size: 64 gwei (209 USD of
  gas) for the 43,439 USD repay, 8.4 gwei for 5,815 USD, 0.01-0.8 gwei for small ones.
- Parameters: close factor 0.5, liquidation incentive 1.10, protocol seize share 0.03 (liquidator keeps
  about 6.7% of the repay before the swap fee).

This bot bids at most 50% of simulated gross and never signs more than 0.90 USD of gas, so it can only win
small or neglected cases (accounts left under water for seconds to minutes).

## Loss bound

- Executor reverts unless the USDC gain >= `minProfit`; a lost attempt costs gas only (0.30M gas when the
  account is no longer liquidatable, up to 1.45M when the profit guard trips; 0.005-0.025 USD at 0.009 gwei).
- `maxFeePerGas x gasLimit + 0.02 USD` (L1 fee allowance) < 0.90 USD per send, `maxFeePerGas` <= 0.5 gwei.
- Wallet holds gas only (15 USD, under the 18 USD Base cap). No principal: the repay is a Morpho flash loan.

## Read cost

- Relay: full scan 11 calls x 144 x 26 CU = 41,184; near poll 144 x 26 = 3,744; discovery 144 x 70 = 10,080;
  attempts about 20/day x 350 = 7,000; about 62,000 CU/day, hard-capped in code at 80,000 CU per UTC day.
- Feed: `/logs/base` filter address = mUSDC, topic0 = LiquidateBorrow, about 54 events/day, about 9,000 CU/day.
- Total about 71,000 CU/day = 0.04 USD/day at 1M CU = 0.53 USD.
- On feed `gap`, 429, 503 or timeout the bot re-reads the near list through the relay.

## Known limits

- USDC debt only (mUSDC carried 381 of 492 events). Collateral must have a direct UniV3 pool to USDC:
  WETH, cbBTC, AERO, VIRTUAL, MORPHO, cbXRP, VVV, EURC, or USDC itself. cbETH, wstETH, weETH, LBTC, tBTC and
  WELL collateral is skipped (`opportunity_skip` `unsupported_collateral`).
- On 2026-11-17 38 known borrowers stood under water with >= 5 USDC of debt and none was takeable
  (`scratch/trial-moonwell-base/standing.json`, `acct.py`): 37 hold no supported collateral (bad debt, or cbETH
  collateral) and one (VIRTUAL collateral) reverts `RedeemFailed` because the market has no cash. Market cash
  that day: mUSDC 0.0025 USDC, mcbBTC 0, mcbETH 0, mVIRTUAL 0.68; mWETH 253 WETH, mAERO 677k, mcbXRP 264k. Seized
  mTokens of a cash-less market cannot be redeemed in the transaction, so the bot can win only on collateral
  whose market has cash (today WETH, AERO, cbXRP); the simulation decides per case. Such accounts are examined
  once per 6 h.

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (with `executor=`), `discover`, `scan`, `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`,
`paper_sim`, `send`, `send_result` (`result` won/lost, `gas_used`, `send_block`, `winner_block`, `winner_tx`,
`blocks_after_winner`), `signer_reject`, `feed_error`, `read_budget`.

## Fork proof

`scratch/trial-moonwell-base/proof.py` (reset base 57520472, deploy, guards, nothing-to-take, success
+2.433237 USDC); `scratch/trial-moonwell-base/selftest.py` checks the bot's calldata against `cast calldata`
and the paper override.

## Files

`bot.py`, `run.sh`, `executor-runtime.hex` (paper code override, `eth_getCode` of the fork deployment),
`seed-users.json` (1,068 mUSDC borrowers from Borrow and LiquidateBorrow logs, blocks 49537862-58609862).
