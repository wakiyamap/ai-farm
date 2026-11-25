trial

# trial-aave-polygon

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): Aave v3 Polygon liquidations with native-USDC
debt. Win rate is measured by sending; nothing here counts as expected revenue under the race rule.

## What it does

1. Waits on the farm feed for `LiquidationCall` on the Aave v3 Pool `0x794a61358d6845594f94dc1db02a252b5b4814ad`
   (topic0 `0xe413a321...5286`). One liquidation usually means a price flip that put other users under water.
2. On an event (and about every 60 s as a safety poll, hourly over the whole universe) reads
   `getUserAccountData` for the near-HF list in one Multicall.
3. For a user with HF < 1 and debt >= 5 USD it simulates the exact executor call for each supported pair
   (debt native USDC `0x3c499c54`; collateral WBTC, WETH, WPOL or USDC; UniV3 fee 500 then 3000) and keeps the best.
4. Live: sends `liquidate(...)` on its executor when simulated gross > the signed gas cap. The executor
   flash-borrows the cover from Morpho (`0x1bf0c254...`), calls `liquidationCall`, swaps the seized collateral
   on UniV3 (SwapRouter02 `0x68b34658...`), repays, and reverts unless the USDC balance grew by `minProfit`
   (= the gas cap). Paper: logs `paper_sim`.

USDT-debt positions (69 of 172 events in 7 d) are out of scope: the profit would be USDT, which the farm does
not count or sweep.

## Competition, last 7 days (to 2026-11-17, attempts:1741)

- 172 `LiquidationCall` events in 168 txs (blocks 97175859-97478259), 18 liquidator addresses:
  `0xc36d7053` 90, `0xa0000470` 17, `0xe7da256e` 14, `0x5ac9bc14` 11, `0xf000042d` 10, `0x62581620` 8,
  twelve others 1-5 each. 75 events are in this bot's scope.
- Blocks to take (all 75, `scratch/trial-aave-op/parent-hf.json`): 71 flipped inside the capture block;
  4 were under water at the parent block (three for 1 block = about 2 s, one for 5-29 blocks).
- Priority fees (18 sampled, `scratch/trial-aave-polygon/tips.json`): base fee 243-270 gwei; in-block flips
  tip 70-156 gwei (median 124) at tx index 18-285; the parent-underwater cases tipped 88 gwei (0.41 USDC
  cover), 555 gwei (1.05 USDC), 793 gwei (467.5 USDC) and 1,977,745 gwei (22,483 USDC, 1,716 POL of gas).
- Entry contracts in the sample: `0x0df29d38` (8 of 18, rotating sender EOAs), `0xe7da256e` 3, `0xa0000470` 2,
  five others once each. Whether `0x0df29d38` / `0xa0000470` are an OEV-auction route was not checked.

This bot bids at most 50% of simulated gross and never signs more than 0.90 USD of gas, so on the 467.5 USDC
case it would have bid about 12,000 gwei against the winner's 793 gwei, one block or more later. It can only
win cases still open when its scan sees them.

## Loss bound

- Executor reverts unless the gain >= `minProfit`; a lost attempt costs gas only (about 390k-800k gas,
  0.01-0.03 USD at 270-400 gwei and POL 0.0815 USD).
- `maxFeePerGas x gasLimit` < 0.90 USD per send at the Aave oracle POL price, `maxFeePerGas` <= 20,000 gwei.
- Wallet holds POL for gas only (10 USD). No principal: the cover is a Morpho flash loan.

## Read cost

- Relay: near scan 1440 x 26 CU = 37,440; full scan 4 calls x 24 x 26 = 2,496; discovery 144 x 70 = 10,080;
  about 50,000 CU/day, hard-capped in code at 75,000 CU per UTC day.
- Feed: `/logs/polygon` filter address = Pool, topic0 = LiquidationCall, about 25 events/day, about 7,000 CU/day.
- Total about 57,000 CU/day = 0.03 USD/day at 1M CU = 0.53 USD.
- On feed `gap`, 429, 503 or timeout the bot re-reads the near list through the relay.

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (with `executor=`), `discover`, `scan`, `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`,
`paper_sim`, `send`, `send_result` (`result` won/lost, `gas_used`, `send_block`, `winner_block`, `winner_tx`,
`blocks_after_winner`), `signer_reject`, `feed_error`, `read_budget`.

## Fork proof

`scratch/trial-aave-polygon/proof.py` (reset polygon 97323754, deploy, guards, success +26.749708 USDC,
exhausted); `scratch/trial-aave-polygon/selftest.py` checks the bot's calldata against `cast calldata` and the
paper override (26.749706 USDC at block 97323754).

## Files

`bot.py`, `run.sh`, `executor-runtime.hex` (paper code override, `eth_getCode` of the fork deployment),
`seed-users.json` (710 borrowers: onBehalfOf of every native-USDC Borrow in 30 d + users liquidated in 7 d).

## Cover sweep (added 2026-11-17, run 039e2c1e)

For a debt of 2,000 USD or more the bot no longer simulates one size only. Per collateral and fee tier it tries
103, 50, 25, 12, 6 and 3 % of the debt, largest first, and stops at the first size that gains less than the one
before; the best size over all routes is sent. Reason: the seized collateral is sold in one UniV3 pool, and past
some size the slippage is larger than the liquidation bonus, so the flash-loan repayment fails (Morpho
`transferFrom reverted`) and the old single size never simulated on the largest borrowers. A revert with
`HealthFactorNotBelowThreshold()` (`0x930bb771`) ends the attempt at once. Debts under 2,000 USD keep the single
full over-cover (a smaller cover on a small debt reverts `MustNotLeaveDust()`).

Evidence (`scratch/aave-sweep-port/`): `harness.py polygon` at the parent of block 97221928 (borrower `0x1039d569...`, 44,956 USD debt, HF 0.99977): old code 2 reverts and no send, new code cover 5,394.70 USDC, gross 229.83 USD; fork proof `proof_polygon_sweep.py`: full cover reverts, swept cover pays +229.827318 USDC (tx `0x3facecce7b8582af9a9aa861d2ac82279cf06c62607c305ff0791dab3ca99fb9`). `regress.py`: the original proof case is unchanged (26.749706 USDC).
Read cost: up to 6 `eth_call` per route and fee tier instead of 1, only for debts of 2,000 USD or more
(about 20 calls = 520 CU for the polygon case above); inside the 75,000 CU/day cap already in the code.
