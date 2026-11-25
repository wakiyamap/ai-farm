trial (cheap-chain trial bot, decision 2026-11-17-cheap-chain-trials): HyperLend liquidations on HyperEVM, USDC debt.

# trial-hyperlend-hyperevm

## What it does
HyperLend core Pool `0x00a89d7a5a02160f20150ebea7a2b5e4879a1a8b` is an Aave v3 fork: `liquidationCall` is open to
anyone and pays the liquidation bonus (about 9 % on WHYPE in the fork proof). For a borrower with USDC debt and
WHYPE, kHYPE or USDC collateral whose health factor is under 1, the bot calls its executor once:
Morpho Blue flash loan of USDC -> `liquidationCall` -> sell the seized collateral on UniV3-style pools
(WHYPE/USDC `0x6c9a33e3...`, kHYPE/WHYPE `0xbe352daf...`) -> repay -> revert unless the USDC balance grew by
`minProfit` -> pay the gain to the bot wallet as USDC. No principal; the wallet holds HYPE for gas only.

Triggers: the farm feed (`/logs/hyperevm`, Pool `LiquidationCall`, topic0 `0xe413a321...`; 112 events in 7 d, not a
busy event) and a ~55 s safety scan of the 200 health factors nearest to 1. After a feed event the near list is
rescanned 8 times, 2 s apart (in a burst the next users flip within seconds). Universe: 1,097 borrowers seeded from
30 d of Borrow logs, extended every 10 min from Borrow/Withdraw logs; full scan hourly.

## Last 7 days of competition (blocks 50,931,683-51,536,483, `scratch/trial-hyperlend/competition.json`)
- 112 `LiquidationCall` on this pool by 20 liquidator contracts: 0x5ac9bc14 24, 0x86885a82 20, 0xdd8692bc 17,
  0x372f8541 11, 0x56d2e869 9, 0x98ff6022 6, others 1-4 each. Part of the flow goes through the permissioned RedStone
  auctioneer wrapper 0x7a0ea1f7 (28 of 61 takes in the earlier window of attempts:1188; not counted again here);
  the rest call the pool as anyone can.
- In scope (USDC debt, WHYPE / kHYPE / USDC collateral): 56. Under water before the take (archive
  `getUserAccountData`): 1 block earlier 35, 3 blocks (3 s) 17, 10 blocks 11, 60 blocks 9.
- With more than 50 USD of debt: 1 block earlier 23, 3 blocks 7, 10 blocks 1, 60 blocks 0. So real size is taken
  within 3-9 s; what stays for a minute is dust (0.1-2 USD of debt, gross of cents).
- Priority fee level: the 7 takes that were under water 3 blocks earlier (all in the 2026-11-13 burst) paid a
  priority fee of 110-15,139 gwei (median 250) on a base fee of 10-262 gwei (normal base fee: 0.1 gwei), i.e.
  0.09-16.8 HYPE of gas per take, roughly half of the gross. Small blocks hold 2M gas, so in a burst block space
  itself is auctioned.
- What this means for the trial: with the trial cap of 1 USD per transaction the bot can pay at most about 16 gwei
  (0.90 USD / HYPE price / gas limit). It can win (a) dust and small positions in quiet times (base fee 0.1 gwei) and
  (b) the occasional burst case while the base fee is still under ~8 gwei. Burst cases at 60-260 gwei base fee are
  logged as `opportunity_skip` (`gross_not_above_gas_cap`) and not sent; that count is the measurement of what a
  higher per-transaction cap would reach.

## Evidence that the executor pays (`scratch/trial-hyperlend/`)
- `selftest.py` (archive `eth_call`, executor as code override, paper lane) on four real past cases, 3 blocks
  before the public taker: +147.33 USDC (borrower 0x959b954f, 25 % cover), +38.41 (0xdd91c296), +141.02
  (0x60d12ab4), +1,925.14 (0x62016b34, kHYPE route). After the capture the same call reverts `0x930bb771`.
- `proof_head.py` (fork at head 51,536,9xx; a position made on the fork and aged 12 h): success tx
  `0x507ccc77...` +196.049242 USDC for 526,700 gas; healthy / non-owner / NoProfit / nothing-left reverts.
- `proof.py`: the same proof at the past block 51,273,260 (borrower 0x959b954f). It could not run on 2026-11-17
  (research lane without Alchemy budget; the fork's public nodes returned inconsistent past state). Run it when the
  lane has budget.

## Loss guard
- Executor reverts `NoProfit()` unless USDC grew by `minProfit` (= the signed gas cap in USDC); a lost attempt
  costs gas only.
- `maxFeePerGas x gasLimit < 0.90 USD` at the pool oracle's HYPE price; gas limit = estimate x 1.25, never above
  1,900,000 (HyperEVM limit 2,000,000).
- Sends only when simulated gross > that gas cap. Priority bid at most 50 % of gross.
- Capital 10 USD of HYPE, no top-up.

## Logs (`logs/bot.jsonl`, one JSON object per line)
`start` (with `executor=`), `scan`, `discover`, `feed`, `opportunity`, `opportunity_skip`, `simulate_revert`,
`paper_sim`, `send`, `send_result` (won / lost, `gas_used`, `send_block`, `winner_block`, `blocks_after_winner`),
`signer_reject`, `read_budget`.

## Read cost (live = paper)
- near scan: 1 Multicall `eth_call` per ~55 s = 1,570 x 26 CU = 40,800 CU/day
- full scan: 6 calls per hour = 144 x 26 = 3,700 CU/day
- discovery: `eth_getLogs` + `eth_blockNumber` every 10 min = 144 x 70 = 10,100 CU/day
- burst rescans: 8 x 26 CU per feed batch, about 16 events/day = 3,300 CU/day
- per opportunity: about 8-14 calls (300 CU)
- total about 58,000 relay CU/day + feed about 7,000 CU/day = 65,000 CU/day = 0.034 USD/day at 0.53 USD per 1M CU.
  The code stops relay reads at 75,000 CU per UTC day.

## Live
`EXECUTOR_ADDR_HYPEREVM` or `EXECUTOR_ADDR` must be set (the bot exits otherwise); the fork address is used only in
paper mode with a code override. Sends go through `farmbot_signer` (`/opt/farm/lib` is appended to `sys.path`).
