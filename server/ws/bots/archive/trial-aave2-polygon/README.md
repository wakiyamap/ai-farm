trial

# trial-aave2-polygon

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): liquidations on Aave v2 Polygon, a frozen
market that still liquidates about 38 positions a day. Win rate is measured by sending; nothing here counts
as expected revenue under the race rule.

## What it does

1. Waits on the farm feed for `LiquidationCall` on the Aave v2 LendingPool
   `0x8dff5e27ea6b7ac08ebfdf9eb090f32ee9a30fcf` (topic0 `0xe413a321...5286`).
2. On an event (and about every 60 s as a safety poll, hourly over the whole universe) reads
   `getUserAccountData` for the near-HF list in one Multicall.
3. For a user with HF < 1 and debt >= 0.001 ETH (about 2 USD) it simulates the exact executor call for each
   supported pair (debt USDC.e, USDT or DAI; collateral WETH, WBTC, WPOL, AAVE, USDC.e or DAI; up to three
   UniV3 routes per pair) and keeps the best.
4. Live: sends `liquidate(...)` on its executor when simulated gross > the signed gas cap. The executor
   flash-borrows the cover from the Balancer V2 Vault (`0xba122222...`), calls `liquidationCall`, sells the
   seized collateral on UniV3 (SwapRouter02 `0x68b34658...`), repays, sells the surplus debt token for native
   USDC (`0x3c499c54...`, fee tier 100) and reverts unless the USDC balance grew by `minProfit` (= the gas
   cap). Paper: logs `paper_sim`.

## Competition, last 7 days (to 2026-11-18 08:43Z, attempts:2065)

- 266 `LiquidationCall` events in 167 txs (blocks 97,120,774-97,523,974), 11 liquidator addresses:
  `0x5ac9bc14` 198, `0x83379b15` 26, `0x953c1ba7` 19, `0xc36d7053` 12, `0xc2fa2aa3` 4, `0xf8aa3b83` 2,
  five others once each. 260 events are in this bot's debt scope: cover sum 4,395 USD, median 0.57,
  p90 14.8, max 1,867; 42 events >= 5 USD, 23 >= 20, 8 >= 100.
- Blocks to take (`scratch/aave2-l2/polygon-parents.json`, the 45 events with cover >= 3 USD): 38 flipped
  inside the capture block; 7 were under water at the parent block (56 USD of cover in total). 38 events
  are same-asset positions (USDC.e/USDC.e, DAI/DAI) that cross HF 1 by interest alone; the large ones are
  taken at tx index 0 of the first block.
- Sample of 17 (`scratch/aave2-l2/polygon-sample.json`): base fee 244-268 gwei; in-block flips tip
  75-117 gwei at tx index 51-208; the index-0 same-asset take of 1,867 USDC.e tipped 551,928 gwei (368 POL);
  dust (0.2-2.6 USD cover) stayed under water 30 to 3,000+ blocks and was taken with a 26-30 gwei tip.
  Gas used 0.65M-2.4M per winner tx.

This bot bids at most 50% of simulated gross and never signs more than 0.90 USD of gas. It can only win
cases still open when its scan sees them: the parent-underwater share (about 3 USD of bonus per week) and
small positions left under water for minutes. Expect cents per day at best.

## Limits

- The universe starts from the 152 users liquidated in the last 45 days who still owe >= 0.0005 ETH
  (`seed-users.json`, built by `scratch/trial-aave2-polygon/seed.py`), and grows from the pool's own logs.
  A borrower who was never liquidated or active in that time is unknown to the bot until someone else
  liquidates them (a partial liquidation leaves them near HF 1, so the next one is in reach). A full list
  needs the debt-token holders (Polygon Blockscout refuses automated reads) or a Borrow-log backfill to 2021.
- Sizing treats USDC.e, USDT and DAI as 1 USD. The first cover over-covers the whole debt; Aave caps the
  repayment and the rest of the flash loan goes straight back.
- USDT and DAI payout routes (debt -> native USDC, fee 100 then 500) are simulated before every send but
  were not fork-proven on a historical case; both proof cases have USDC.e debt.

## Loss bound

- Executor reverts unless the gain >= `minProfit`; a lost attempt costs gas only (about 360k-1.0M gas,
  0.01-0.02 USD at 240-280 gwei and POL 0.078 USD).
- `maxFeePerGas x gasLimit` < 0.90 USD per send at the Aave oracle POL price, `maxFeePerGas` <= 20,000 gwei.
- Wallet holds POL for gas only (10 USD). No principal: the cover is a Balancer V2 flash loan.

## Read cost

- Relay: near scan 1440 x 26 CU = 37,440; full scan 2 calls x 24 x 26 = 1,248; discovery 144 x 70 = 10,080;
  about 49,000 CU/day, hard-capped in code at 75,000 CU per UTC day.
- Feed: `/logs/polygon` filter address = LendingPool, topic0 = LiquidationCall, about 38 events/day,
  about 8,000 CU/day.
- Total about 57,000 CU/day = 0.03 USD/day at 1M CU = 0.53 USD.
- On feed `gap`, 429, 503 or timeout the bot re-reads the near list through the relay.

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (with `executor=`), `discover`, `scan`, `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`,
`paper_sim`, `send`, `send_result` (`result` won/lost, `gas_used`, `send_block`, `winner_block`, `winner_tx`,
`blocks_after_winner`), `signer_reject`, `feed_error`, `read_budget`.

## Proof

`scratch/trial-aave2-polygon/proof.py` (two historical cases, PROOF OK) and `selftest.py`; see
`fork_evidence` in the manifest.
