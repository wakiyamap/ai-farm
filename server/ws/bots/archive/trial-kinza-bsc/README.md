trial

# trial-kinza-bsc

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): liquidations on Kinza Finance, an Aave-v3 fork
on BNB Smart Chain that is winding down (0 Borrow and 0 Supply logs in 7 days, only Withdraw, Repay and
LiquidationCall). Win rate is measured by sending; nothing here counts as expected revenue under the race rule.

## What it does

1. Waits on the farm feed for `LiquidationCall` on the Kinza Pool `0xcb0620b181140e57d1c0d8b724cde623ca963c8c`
   (topic0 `0xe413a321...5286`). One liquidation usually means a price flip that put other users under water.
   Users named in those events join the watched universe.
2. On an event (and about every 60 s as a safety poll, hourly over the whole universe) reads
   `getUserAccountData` for the near-HF list in one Multicall.
3. For a user with HF < 1 and debt >= 5 USD it simulates the exact executor call for the user's supported pairs
   (debt USDC, USDT, FDUSD or WBNB; collateral BTCB, WBNB, ETH, USDT or USDC), PancakeSwap V3 fee 500 first, covers of
   103%, 50%, 25% of the debt first, and takes the first combination that simulates (speed first: 0.45 s
   blocks); other fee tiers (100, 2500) and smaller covers follow, at most 40 simulations per user.
4. Live: sends `liquidate(...)` on its executor when simulated gross > the signed gas cap. The executor
   flash-borrows the cover from the Aave v3 BSC Pool `0x6807dc92...` (`flashLoanSimple`; Kinza is only the
   liquidated pool), calls Kinza `liquidationCall`, swaps the seized collateral on PancakeSwap V3
   (`0x1b81d678...` SwapRouter), repays with the premium, swaps a USDT or FDUSD gain to USDC (fee 100) or unwraps a WBNB
   gain, and reverts unless the pay-token balance grew by `minProfit` (= the gas cap). The bot wallet is paid
   in USDC or native BNB. Paper: logs `paper_sim`.

## Competition, last 7 days (blocks 133,056,979-134,400,979, to 2026-11-18 23:40Z)

Data: `scratch/trial-kinza-bsc/liq-rows.json` (census), `parent-hf.json`, `tips.json`.

- 589 `LiquidationCall` events in 228 txs, 580 distinct users. Per day: 39, 61, 213, 54, 214, 3, 5 (bursts on
  BNB price drops). Liquidator contracts by events: `0x5ac9bc14` 254, `0x6094c56b` 66, `0xc4cd094a` 62,
  `0x0000000000be226a` 45, `0x8ea4c159` 45, `0x494261a2` 41, `0x50b2e230` 24, others below 20.
- 546 of the 589 are dust (median cover 0.25 USDT / 0.16 USDC, swept in batches). 43 events have a cover above
  5 USD (largest 478.96 USDT, bonus about 7.1%): debt USDT 29, USDC 5, WBNB 5, FDUSD 4;
  collateral WBNB 25, USDC 12, USDT 3, others 3. Takers of the 43: `0x5ac9bc14` 19, `0xe65f1199` 5,
  `0x697f6e97` 5, `0xf000042d` 3, `0xd1fa4cef` 3, six others 1-2; 17 sender EOAs.
- Blocks to take: of the 43, 35 flipped inside the capture block; 8 were under water at the parent block
  (0.45 s before) and also 2 blocks before; none 8 blocks before.
- Gas price of the winners (43 receipts): min 0.05, median 0.1, p90 0.3, max 1.0 gwei; median gas 765,544,
  median cost 7.0e-5 BNB (about 0.044 USD at BNB 625 USD). 28 of 43 sit at tx index <= 5 while paying about
  the floor, so their position is bought outside the gas price (builder bundles), which this bot does not do.
  10 sit at index >= 20.

This bot bids at most 50% of simulated gross and never signs more than 0.90 USD of gas, so it can only win
users left under water for a block or more and the takes nobody bundles (8 of 43 in the census; the proof case
sat at tx index 50 at the 0.05 gwei floor).

## Loss bound

- Executor reverts unless the gain >= `minProfit`; a lost attempt costs gas only (0.42-1.02M gas for a revert
  on the fork, 0.013-0.03 USD at 0.05 gwei, at most 0.90 USD at the signed cap).
- `gasPrice x gasLimit` < 0.90 USD per send, gas price <= 3 gwei, gas limit <= 3,000,000.
- Wallet holds gas only (12 USD of BNB). No principal: the cover is an Aave flash loan repaid in the tx.

## Read cost

- Relay: near scan 1440 x 26 CU = 37,440; full scan 5 calls x 24 x 26 = 3,120; discovery 144 x 85 = 12,240;
  about 53,000 CU/day, hard-capped in code at 75,000 CU per UTC day.
- Feed: `/logs/bsc` filter address = Kinza Pool, topic0 = LiquidationCall, about 84 events/day in 33 txs/day
  (bursts of 200/day), about 8,000 CU/day.
- Total about 61,000 CU/day = 0.03 USD/day at 1M CU = 0.53 USD.
- On feed `gap`, 429, 503 or timeout the bot re-reads the near list through the relay, then waits 30 s.

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (with `executor=`), `discover`, `scan`, `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`,
`paper_sim`, `send`, `send_result` (`result` won/lost, `gas_used`, `send_block`, `winner_block`, `winner_tx`,
`blocks_after_winner`), `signer_reject`, `feed_error`, `read_budget`.

## Fork proof

`scratch/trial-kinza-bsc/proof.py` (reset bsc 133299629 = parent of the real take `0x24ae9f0b...` of user
`0x5b278c6c...`, HF 0.99456; deploy, non-owner and NoProfit guards, success +2.481795 USDC on the USDT debt
through the exit swap, second call reverts with Aave error 45). `scratch/trial-kinza-bsc/selftest.py` checks
the bot's calldata against `cast calldata` for all three debt tokens (Aave pool as lender, Kinza pool in the
job) and runs the bot's own `attempt()` pinned to the proof block (one opportunity: it takes the user's USDC
debt first, 0.999 USD gross against a 0.50 USD gas cap; the USDT debt of the same user was worth 2.48 USD, the
bot trades that for speed) and 8 blocks earlier (HF 1.0052, nothing).

`scratch/trial-kinza-bsc/proof_fdusd.py`: FDUSD debt (reset 133621097 = parent of the real take `0x1acfeda7...`
of user `0xb451c775...`, HF 0.99968): NoProfit guard, success +1.236186 USDC (WBNB -> FDUSD fee 500, FDUSD ->
USDC fee 100, 1,564,977 gas), second call reverts. In the self-test the bot again takes that user's USDC debt
first (0.653 USD gross, gas cap 0.33 USD). The WBNB-debt path (unwrap to native) is checked by calldata only.
The bsc fork upstream sometimes answers `missing trie node` for old state; repeat a failed run after `fork reset`.

## Known limits

- Universe: 972 seed users (580 liquidated in 7 d + users of Withdraw / Repay logs in blocks
  128,736,979-134,400,979, about 29 days; no Borrow or Supply log exists in that range). Older borrowers that
  did nothing for 29 days are missing until they appear in a Withdraw log or a LiquidationCall.
- The three minor debt tokens (`0xb0b84d29`, `0x40af3827`, `0x0782b6d8`; 133 of the 589 events, all dust) are
  not taken.
- A user with several debts is taken on the first debt that simulates (USDC, USDT, FDUSD, WBNB order), not the
  one with the largest gain.

## Files

`bot.py`, `run.sh`, `executor-runtime.hex` (paper code override, `eth_getCode` of the fork deployment),
`seed-users.json`.
