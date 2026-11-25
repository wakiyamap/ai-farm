trial — Aave V4 liquidations on the Avalanche Core Hub spoke (cheap-chain trial, decision 2026-11-17-cheap-chain-trials.md)

# trial-aave4-avalanche

**What it does.** Aave V4 on Avalanche (Core Hub `0xd07369fAE4A5BB13c9Ce446B052c7867B1AbDf6e` from the DefiLlama aave-v4 adapter; spoke `0x435272ceff93a1e657e8abfdf0a13e95900a3a56`, the only emitter of LiquidationCall on the chain in 7 days; 6 reserves, 7.65M USDC borrowed). `liquidationCall(collateralReserveId, debtReserveId, user, debtToCover, receiveShares)` on the spoke is open to anyone and pays the liquidator the collateral at a bonus. The bot takes USDC-debt positions (reserve 2) whose collateral is WAVAX (0), BTC.b (1), WETH.e (4) or USDC (2), in one transaction through its executor `TrialAave4TakeAvax`: Aave V3 `flashLoanSimple` of USDC (pool `0x794a61358D6845594F94dc1DB02A252b5b4814aD`, 5 bps premium, 5.47M USDC available), `liquidationCall`, sale of the seized collateral on UniV3 pools (WAVAX/USDC 0.05% `0xfae3f424...`; BTC.b/USDC `0x2e587b9e...` or BTC.b/WAVAX `0xfc1e7bc6...` then WAVAX/USDC; WETH.e/WAVAX `0x7b602f98...` then WAVAX/USDC), repayment, USDC gain to the bot wallet, or revert `NoProfit()`. Flash source and WAVAX pool are the ones the incumbents use (callTracer of `0x1848868a...`, `0xc9e9b0f4...`).

**Sister bots.** `trial-aave4-optimism`, `trial-aave4-base` (same spoke ABI, same LiquidationCall topic, same feed loop). Differences: Aave V3 flash loan instead of Morpho (no Morpho Blue on Avalanche in the incumbents' traces), gas cap valued at the spoke oracle's AVAX price, one aggregator on the feed.

## Competition, last 7 days (blocks 100,140,245-100,820,693)

Source: `scratch/trial-aave4-avalanche/scan.py` (topic-only `eth_getLogs` for LiquidationCall `0x2a1f12d9...`, with a same-shape control on optimism), `recon.py` (every tx, receipt, health factor at the blocks before the take; `windows.json`).

- 12 liquidations, all on this spoke, all USDC debt. Collateral: WAVAX 8, BTC.b 3, WETH.e 1.
- Takers (tx.to): `0x6ebfb34731d9714afe453ff447bc9441b25e88c8` 4 (EOA `0x58d15e7f...`), `0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd` 2 (EOA `0xd9fffdf0...`, also the main taker on optimism), `0x3dbddadf5d0c933e6827af9a58836dd3338b7205` 2, `0x11df212054e561ab512b0011ac43a2907e705034` 2, `0xf86efcf912e59f82318081b9ec2884b8ec779d77` 1, `0xff296e47bb9d934c6850d9e2d25503e2a971eee7` 1.
- Blocks from liquidatable to taken (health factor at block - 1, about 1 s blocks): 6 of 12 were taken in the block in which they became liquidatable (parent HF 1.0003-1.0049; priority fee 0.66-27 gwei, tx index 3-83), 6 one block later (parent HF 0.9978-0.9993). None stood 2 blocks.
- Priority fee of the 6 one-block-late takes: 873, 1,150, 20,078, 43,756, 46,758 gwei (tx index 0-1; 1.0-112 AVAX of fees per take, about half of the gross: `0xc7b17dcc...` paid 46.27 AVAX and kept 88.73 WAVAX) and once 22 gwei (`0xc6e96719...`, block 100,333,136, tx index 63, fee 0.029 AVAX, kept 45.66 USDC; the fork-proof case).
- Gross kept by takers where it shows as a token flow: 0.02, 45.66, 143.99, 192.0, 1,685 and 3,505 USDC; 45.6, 88.7 and 100.0 WAVAX. Gas per take 724,750-2,500,000 (median about 1.0M), base fee 8-39 gwei.

**What the bot aims at.** Takes still open about 1 s after the price update whose winner does not bid in the thousands of gwei (1 of the 6 in 7 days: 22 gwei). With a gas cap under 1 USD (ceiling about 98 gwei on 1.3M gas at AVAX 7 USD) the bot cannot win the fee auctions on the large takes; it bids up to 50% of its simulated gross inside that ceiling. Honest expectation: 0-1 wins per week.

## Trigger

A borrower becomes liquidatable when the spoke oracle's price moves, and that moves only when the Chainlink aggregator behind a reserve's source emits `AnswerUpdated(int256,uint256,uint256)` (topic0 `0x0559884f...46fc5f`). Traced with `scratch/trial-aave4-avalanche/recon2.py` (`recon2.json`): `oracle.getReserveSource(id)` -> `aggregator()`.

| Reserve | Source | Aggregator | AnswerUpdated, last 10,000 blocks (2.5 h) |
|---|---|---|---|
| 0 WAVAX | `0x0a77230d17318075983913bc2145db16c7366156` "AVAX / USD" | `0xcfbfe648ba88bf7d9776d970417a0b26c315feb4` (on the feed) | 109 (about 1,050/day) |
| 1 BTC.b | `0x2779d32d5166baaa2b2b658333ba7e6ec0c65743` "BTC / USD" | `0xa9afa74ddac812b86eeaa60a035c6592470f4a48` | 44 |
| 4 WETH.e | `0x976b3d034e162d8bd72d6b9c989d545b839003b0` "ETH / USD" | `0x9ff520924dc295074f43a8a01ee30a4d39a4223b` | 54 |
| 2 USDC | `0xb0d7a8bb...` -> `0xf0968726...` "USDC / USD" | `0xb051a0a13fe913c6c723ac7111a17508081dbd3a` | 0 |

Only AVAX / USD is on the feed (8 of the 12 takes had WAVAX collateral; all three would cost about 2,000 deliveries a day and pass 100,000 CU). BTC.b and WETH.e crossings are seen at the next AVAX / USD delivery (about every 80 s) or the 5-minute safety poll.

Feed rules in code (`bot.py` `main`): `gap: true` or a `removed` log -> one re-read of the near set; HTTP 429 / 503 / connection error -> `feed_error`, one re-read (at most one per 60 s while the feed stays down), sleep 5 s, same cursor; 5 minutes without a delivery -> `safety_poll`. Feed slots on avalanche at placement: 3 of 16 in use (`/health`, 2026-11-19 23:46Z).

## Read cost (live, Alchemy CU/day)

- Feed filter: about 1,050 logs/day x about 660 bytes x 0.04 CU = 27,700 CU, plus 3-4 CU/min idle (up to 5,800): about 34,000 CU.
- One near-set Multicall `eth_call` (26 CU) per delivery: 1,050 x 26 = 27,300 CU.
- Safety poll: at most 288 x 26 = 7,500 CU (in practice few: a delivery comes about every 80 s).
- Full scan every 12 h: 6 Multicalls (531 borrowers) + about 5 getLogs (10,000-block pages) + 1 blockNumber = about 540 CU, x 2 = 1,100 CU.
- Per attempt 4 reads = 88 CU; per send up to 20 receipt polls + 2 = 500 CU.
- Total about 65,000 CU/day = 0.034 USD at 1M CU = 0.53 USD; relay hard cap in code 60,000 (`CU_CAP`), the feed filter is on top, so under 100,000 in every case. Feed unreachable all day: one re-read per 60 s = 37,440 CU.

## Loss guard

- Executor: `take()` reverts `NoProfit()` unless its USDC balance grows by `minProfit` after the flash premium (`TrialAave4TakeAvax.sol:89`); the bot passes its gas cap in USD as `minProfit`.
- Gas: `GAS_LIMIT` 1,300,000 x maxFeePerGas <= 0.90 USD at the spoke oracle's AVAX / USD price read in the same Multicall as the position (`bot.py:338-344`); never above 300 gwei; the bot does not send unless the cap is under 1 USD and the simulated gross is above it.
- Capital 10 USD of AVAX for gas, no principal: the USDC comes from the flash loan.

## Files

- `bot.py`; `seed-borrowers.json` 531 borrowers from the spoke's Borrow logs (blocks 89,721,383-100,820,902; new ones are added at every full scan); `executor-runtime.hex` = `eth_getCode` of the fork deployment (paper code override).
- Logs: `logs/bot.jsonl` rows `start`, `feed`, `feed_gap`, `feed_error`, `discover`, `scan` (label `oracle_update` / `safety_poll` / `gap` / `full`, min_hf), `candidate_skip`, `simulate_revert`, `opportunity_skip`, `opportunity`, `paper_sim`, live `send_result` (result won / lost, gas_used, winner_block, blocks_after_winner), `signer_reject`, `read_budget`.
- Proof and measurements: `scratch/trial-aave4-avalanche/` (`proof.py`, `proof-result.json`, `selftest.py`, `selftest-result.json`, `scan.py`, `recon.py`, `recon2.py`, `windows.json`, `seed.py`).

## Not done

- BTC.b and WETH.e routes are not fork-proven: none of their 4 takes was liquidatable at a parent block. The bot simulates before every send, so a broken route costs nothing.
- USDt, WAVAX or WETH.e debt (none in the 7-day window) is out of scope.
- After 7 days live or when the capital is spent: sends, wins, net as an `attempts` row; lead 310.
