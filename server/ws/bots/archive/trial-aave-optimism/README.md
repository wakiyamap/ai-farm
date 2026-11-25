trial

# trial-aave-optimism

Cheap-chain trial (decision `2026-11-17-cheap-chain-trials.md`): Aave v3 OP Mainnet liquidations. Win rate is
measured by sending; nothing here counts as expected revenue under the race rule.

## What it does

1. Waits on the farm feed for `LiquidationCall` on the Aave v3 Pool `0x794a61358d6845594f94dc1db02a252b5b4814ad`
   (topic0 `0xe413a321...5286`). One liquidation usually means a price flip that put other users under water.
2. On an event (and about every 60 s as a safety poll, hourly over the whole universe) reads
   `getUserAccountData` for the near-HF list in one Multicall.
3. For a user with HF < 1 and debt >= 5 USD it simulates the exact executor call for each supported pair
   (debt native USDC or WETH; collateral WETH, WBTC or USDC; UniV3 fee 500 then 3000) over a falling list of
   cover sizes (103%, 50%, 25%, 15%, 7%, 2% of the debt) and keeps the best. The cover list exists because a
   cover larger than the chosen collateral can pay for reverts when the user holds several collaterals
   (fork proof: 16k and 32k USDC revert, 5,595 USDC succeeds).
4. Live: sends `liquidate(...)` on its executor when simulated gross > the signed gas cap. The executor
   flash-borrows the cover from Morpho Blue (`0xce95afbb...`, 90k USDC and 212 WETH at 2026-11-17), calls
   `liquidationCall`, swaps the seized collateral on UniV3, repays, and reverts unless the debt-token balance
   grew by `minProfit` (= the gas cap). Paper: logs `paper_sim`.

## Competition, last 7 days (blocks 159359639-159662039, to 2026-11-17)

Data: `scratch/trial-aave-op/logs-op-rows.json` (census), `scratch/trial-aave-optimism/parent-hf.json`, `tips.json`.

- 59 `LiquidationCall` events, 10 liquidator contracts: `0x5ac9bc14` 15, `0xa4523d14` 12, `0x8b3ada08` 9,
  `0xa24b73b8` 6, `0x8e0ff45d` 6, `0x27ead500` 4, `0xf000042d` 3, `0x03c8c602` 2, `0xb475e5da` 1, `0xb90a9b12` 1.
- 23 events have native-USDC debt (WBTC 11, WETH 9, wstETH 2, USDC 1 as collateral); covers 0.11-31,364 USDC.
  wstETH collateral (2 events, 48k USDC) is out of scope: no single-hop route to USDC.
- Blocks to take: 18 of 23 flipped inside the capture block; 5 were under water at the parent block (2 s
  before) and healthy 2 blocks before. Tx index of the capture 1-230.
- Priority fees: the big same-block takers pay a lot (`0x8e0ff45d` 73-242 gwei on covers of 2.7k-12.5k USDC,
  `0x5ac9bc14` 6-386 gwei, `0xa4523d14` 0.76-9.2 gwei), i.e. 36-660 USD of gas per take. But four takes went
  almost for free: `0xf000042d` 1,105 USDC at 0.001 gwei and 3,242 USDC at 0.00003 gwei, `0xb475e5da`
  763 USDC at 0.0003 gwei, `0x2c170622` 3,286 USDC at 0.0001 gwei; dust takes (0.1-0.8 USDC) 0.002-0.011 gwei.
- The proof case (5,595 USDC cover, HF 0.99952 at the parent block) was taken at tx index 1 for 91 gwei
  (0.087 ETH of gas).

This bot bids at most 50% of simulated gross and never signs more than 0.90 USD of gas (about 0.33 gwei at
1.37M gas), so it can only win the low-tip class and users left under water after a cascade.

## Loss bound

- Executor reverts unless the gain >= `minProfit`; a lost attempt costs gas only (0.41M-1.1M gas, about
  0.001-0.002 USD at 0.001 gwei plus the L1 fee of about 1e-8 to 1e-7 ETH).
- `maxFeePerGas x gasLimit + 0.02 USD` (L1 fee allowance) < 0.90 USD per send, `maxFeePerGas` <= 0.5 gwei.
- Wallet holds gas only (15 USD, under the 18 USD OP Mainnet cap). No principal: the cover is a Morpho flash loan.

## Read cost

- Relay: near scan 1440 x 26 CU = 37,440; full scan 2 calls x 24 x 26 = 1,248; discovery 144 x 70 = 10,080;
  about 49,000 CU/day, hard-capped in code at 75,000 CU per UTC day.
- Feed: `/logs/optimism` filter address = Pool, topic0 = LiquidationCall, about 8 events/day, about 5,000 CU/day.
- Total about 54,000 CU/day = 0.03 USD/day at 1M CU = 0.53 USD.
- On feed `gap`, 429, 503 or timeout the bot re-reads the near list through the relay.

## Logs (`logs/bot.jsonl`, one JSON object per line)

`start` (with `executor=`), `discover`, `scan`, `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`,
`paper_sim`, `send`, `send_result` (`result` won/lost, `gas_used`, `send_block`, `winner_block`, `winner_tx`,
`blocks_after_winner`), `signer_reject`, `feed_error`, `read_budget`.

## Fork proof

`scratch/trial-aave-optimism/proof.py` (reset optimism 159471567, deploy, guards, success +199.218889 USDC,
exhausted); `scratch/trial-aave-optimism/selftest.py` checks the bot's calldata against `cast calldata` and runs
the bot's own `attempt()` pinned to the proof block (opportunity, 201.54 USDC) and 30 blocks earlier (nothing).

## Files

`bot.py`, `run.sh`, `executor-runtime.hex` (paper code override, `eth_getCode` of the fork deployment),
`seed-users.json` (300 borrowers: 30 d of native-USDC and WETH Borrow logs + users liquidated in 7 d).
