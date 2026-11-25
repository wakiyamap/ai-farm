trial — Aave V4 liquidations on the EtherFi borrowing market spoke, OP Mainnet (cheap-chain trial, decision 2026-11-17-cheap-chain-trials.md)

# trial-aave4-optimism

**What it does.** The EtherFi borrowing market on OP Mainnet is an Aave V4 deployment (hub `0x66753c4e3fC84f1eD0e3C267C927284E9d90C572`, spoke `0xdffcc3536d932eb51df51a7f5fa407c4270d5308`, 30 reserves, 36.8M USDC borrowed). `liquidationCall(collateralReserveId, debtReserveId, user, debtToCover, receiveShares)` on the spoke is open to anyone and pays the liquidator the collateral at a bonus. The bot takes USDC-debt positions (reserve 0) whose collateral is USDC (reserve 0), WETH (reserve 1) or USDT (reserve 2), in one transaction through its executor `TrialAave4TakeOp`: zero-fee Morpho Blue flash loan of USDC (`0xce95AfbB8EA029495c66020883F87aaE8864AF92`), `liquidationCall`, sale of the seized collateral on a UniV3 pool (WETH/USDC `0x1fb3cf6e...`, USDT/USDC `0x84ce89b4...`; no swap when the collateral is USDC), repayment, USDC gain to the bot wallet, or revert `NoProfit()`.

**Sister bot.** `trial-aave4-base` (same spoke ABI, same LiquidationCall topic, same feed loop). Differences: lender, tokens and pool path are call arguments of the executor; three collateral reserves.

## Trigger (fix of 2026-11-19, review run d3010043: the 60 s / 6 s timer is gone)

A borrower becomes liquidatable when the spoke oracle's price moves, and that price moves only when a Chainlink aggregator emits `AnswerUpdated(int256,uint256,uint256)` (topic0 `0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f`, from `cast keccak`). The bot long-polls the farm feed `/logs/optimism` for that log on three aggregators (one filter) and re-reads the 100-borrower near set once per delivery.

Traced with `scratch/trial-aave4-optimism/trigger.py` (result `trigger-result.json`), `oracle.getReserveSource(id)` -> `rateFeed()` -> `aggregator()`; the source of reserve 1 is ether.fi's verified `ChainlinkPriceFeed`, which reads `rateFeed.latestRoundData()` and nothing else:

| Reserve | Source on the spoke oracle | Chainlink proxy | Aggregator (feed filter address) | AnswerUpdated |
|---|---|---|---|---|
| 1 WETH | `0x4060f7d705a32dfc7b96f352e62589c25007e16b` "ETH / USD" | `0x13e3ee699d1909e989722e753853ae30b17e08c5` | `0x16c04812fa9db1d0236c3841dda8e86225bc3f3e` | 1,854 in blocks 159,467,786-159,635,318 = 478/day; 353 in the last 24 h |
| 0 USDC | `0x5b057985496a6ff09bf62c9ba867ae5ddeafa4e0` "Capped USDC / USD" -> `0x7e7a2ea279992c97a826f8842b78446870606048` | `0x16a9fa2fda030272ce99b29cf780dfa30361e0f3` | `0xdb5a1d830b72ce47b881c0093dbc9c6321091e78` | 1/day |
| 2 USDT | `0x7579977643ee68946db95d9cb5ff582674619025` "Capped USDT / USD" -> `0xdc0e7e8076eb0bf30bfb2677d8ef169170df51b3` | `0xecef79e109e997bca29c1c0897ec9d7b03647f5e` | `0xfd7f8e6ba7b6d36f4b3c9013de5fa527d8347643` | 1/day |

Evidence that this log is the trigger: of the 40 WETH-collateral takes in `windows.json`, 39 became liquidatable within 1 block of the last ETH / USD `AnswerUpdated` before the take. Blocks from that update to the take: 0 for 17 takes, 1 for 18, then 2, 3, 4, 7, 16. With the measured feed delivery of about 1 s after the block timestamp the bot's read + simulation + send lands 1-2 blocks (2-4 s) after the update: behind the 17 same-block takes, level with the 18 next-block ones, ahead of the 5 slower ones.

Feed rules in code (`bot.py` `main`): `gap: true` or a `removed` log -> one re-read of the near set (label `gap`); HTTP 429 / 503 / connection error -> log `feed_error`, one re-read (at most one per 60 s while the feed stays down), sleep 5 s, continue with the same cursor; 5 minutes without a delivery -> `safety_poll` re-read; the state acted on is always read through the relay and simulated right before a send. Not covered by the filter: a crossing caused by another collateral's price (weETH, liquidETH, sETHFI... of a mixed position) or by interest accrual (about 1e-9 of health factor per second) is seen by the safety poll only. Aggregator addresses change when Chainlink upgrades a feed: `aggregator()` of the three proxies should be re-read if `feed` rows stop for an hour (bad sign in the manifest).

First paper delivery after the fix (`logs/bot.jsonl`, 2026-11-19 21:45:07Z): `feed` row for block 159,762,965 handled 0.14 s after the block timestamp, `scan` label `oracle_update` written 0.57 s later (min_hf 1.00274, no candidate).

Feed slots on optimism at the fix: 5 of 8 filters in use (`/health`, 2026-11-19 21:42Z); this bot's filter is the sixth. Another bot's filter already includes the ETH / USD aggregator together with `0x07c15082...`; the address lists differ, so they are separate filters.

## Competition, last 7 days (blocks 159,458,932-159,761,332, 2026-11-12 20:50Z to 11-19 20:50Z)

Source: `scratch/ra5c2/liqs.py`, `liqs2.py` (one topic-only `eth_getLogs` for LiquidationCall `0x2a1f12d9...`, every receipt), `scratch/trial-aave4-optimism/windows.py`.

- 139 liquidations, all on this spoke. Takers (tx.to): `0x5ac9bc14376bf2727c6211960cf3cec1e2f295bd` 105 (EOA `0xd9fffdf0...`, Morpho flash, kept 947 USDC + USDT in total, median 2.08, max 120.5), `0x4661f836f07c78a01d5490bff6e8587b9291c6b8` 16, direct calls of the spoke by EOA `0x485ef3...` with its own USDC 9, `0xf000042d2b48921c234f15d167e7874f594f303e` 7, `0xdcb39a676748c29b2ffe5f97fe607d3238f855fb` 2 (kept 44.9 and 10.5 USDC with no priority fee, tx index 12 and 4).
- Collateral / debt reserves: WETH/USDC 40, liquidETH/USDC 29, weETH/USDC 12, USDC/USDC 11, sETHFI/USDC 11, ETHFI/USDC 9, WETH/USDT 8, liquidUSD 6, liquidBTC 5, USDT/USDC 3, others 5.
- In the bot's scope (USDC debt; USDC, WETH or USDT collateral): 54 takes, the takers kept 270 USDC in total, median 0.65.
- Blocks from liquidatable to taken (health factor of the user at the blocks before the take, 2 s blocks): median 1 block. 22 of 54 were taken in the block in which they became liquidatable, 24 one block (2 s) later, 8 stood 4 s or longer, 5 stood 10 s, 4 stood 30 s, 2 stood 5 minutes. The 8: gross 0.002, 4.97 (the fork-proof case: the taker took 4,919 of 8,626 USDC of debt, a full take at the parent block pays 302 USDC), 0.585, 0.027, 1.56, 0.40, 1.24, 1.03.
- Transaction index of the takes: median 43, 6 of 139 at index 1-2: not a first-block job.
- Priority fee: median 0.05 gwei, 90th percentile 4.4 gwei, maximum 21.4 gwei. The main taker bids about 10-40% of its gain on takes above 5 USDC (e.g. 69.0 USDC kept, 0.00487 ETH paid) and 0.003-0.3 gwei on small ones. Gas per take: median 922,507.

**What the bot aims at.** The takes still open 1-2 blocks after the price update: the 18 next-block takes (contested) and the 4-30 s tail. With a 1 USD gas cap (0.15 gwei on 1.3M gas) it cannot outbid the 2-21 gwei bids on the large takes in the same block; it bids up to 25% of its simulated gross.

## Read cost (live, Alchemy CU/day)

- Feed filter: about 480 logs/day x about 660 bytes (measured `eth_getLogs` JSON size 655-657) x 0.04 CU = 12,700 CU, plus 3-4 CU/min idle (up to 5,800): 13,000-19,000 CU.
- One near-set Multicall `eth_call` (26 CU) per delivery: 480 x 26 = 12,500 CU.
- Safety poll after 5 minutes of feed silence: at most 288 x 26 = 7,500 CU (in practice far fewer: the ETH / USD feed updates every 3 minutes on average).
- Full scan every 12 h: 129 Multicalls (12,890 borrowers, 100 per call) + 1 getLogs + 1 blockNumber = 3,440 CU, x 2 = 6,880 CU (measured by the self-test: 4,034 CU for one full scan plus three attempts).
- Per attempt 4 reads (position, 2 simulations, gas price) = 88 CU; per send up to 20 receipt polls + 2 = 500 CU.
- Total about 40,000 CU/day = 0.021 USD at 1M CU = 0.53 USD (at most about 46,000 before attempts); relay hard cap in code 75,000 (`CU_CAP`), the feed filter is on top, so under 100,000 in every case. If the feed is unreachable all day the fallback is one re-read per 60 s = 37,440 CU.

## Loss guard

- Executor: `take()` reverts `NoProfit()` unless its USDC balance grows by `minProfit` (`TrialAave4TakeOp.sol:88`); the bot passes its gas cap in USD as `minProfit`.
- Gas: `GAS_LIMIT` 1,300,000 x `MAX_FEE_WEI` 0.15 gwei = 1.95e-4 ETH (0.35 USD at 1,800 USD/ETH, 0.78 USD at the deliberately high 4,000 used in code) + 0.02 USD L1 data fee allowance; the bot does not send unless that cap is under 1 USD and the simulated gross is above it (`bot.py:334`).
- Capital 18 USD (OP Stack gas wallet cap), no principal: the USDC comes from the flash loan.

## Files

- `bot.py` the bot; `seed-borrowers.json` 12,890 borrowers from the spoke's Borrow logs (blocks 154,915,790-159,761,496; new ones are added at every full scan); `executor-runtime.hex` = `eth_getCode` of the fork deployment (paper code override).
- Logs: `logs/bot.jsonl` rows `start`, `feed` (events, blocks, aggregators, delay_s from block timestamp to handling), `feed_gap`, `feed_error`, `discover`, `scan` (label `oracle_update` / `safety_poll` / `gap` / `full`, min_hf), `candidate_skip`, `simulate_revert`, `opportunity_skip`, `opportunity`, `paper_sim`, live `send_result` (result won / lost, gas_used, winner_block, blocks_after_winner), `signer_reject`, `read_budget`.
- Proof and measurements: `scratch/trial-aave4-optimism/` (`proof.py`, `proof-result.json`, `selftest.py`, `windows.py`, `windows.json`, `recon.py`, `seed.py`), `scratch/ra5c2/liqs2-optimism.json`.

## Not done

- 85 of the 139 takes are outside the scope: liquidETH, weETH, sETHFI, ETHFI, liquidBTC and liquidUSD collateral are sold by the incumbent through Uniswap v4 pools (PoolManager `0x9a13f98cb987694c9f086b1f5eb990eea8264ec3`, unlock callback) and USDT debt needs a USDT flash source. The executor has no v4 step.
- After 7 days live or when the capital is spent: sends, wins, net as an `attempts` row.
