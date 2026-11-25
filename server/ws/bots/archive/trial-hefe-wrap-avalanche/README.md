trial: HEFE / aHEFE two-pool arbitrage through the public BIFKN314Wrapper on Avalanche (decision 2026-11-17-cheap-chain-trials)

## What it does

- aHEFE `0x4c726f6159a883e94b87984d827453f6f5955098` is a BIFKN314 token: the token contract is its own AVAX pool
  (`swapNativeToToken`, `swapTokenToNative`; fee 0.3 pct + 1 pct trading fee).
- BIFKN314Wrapper `0xc6346fe9f72c7ac09710914e98895b9bfba3bfd4` converts aHEFE <-> HEFE 1:1 for anyone (`wrap`, `unwrap`,
  no fee, no role).
- HEFE `0x18e3605b13f10016901eac609b9e188cf7c18973` trades on the Trader Joe V1 pair HEFE / WAVAX
  `0xe11e871d312cc9bae9eb24c7bdc2031f8453bf44` (0.3 pct; HEFE takes a 1 pct tax into and out of the pair).
- When a trade leaves the two prices more than about 2.6 pct apart, one transaction through the executor closes it:
  - unwrap direction (aHEFE cheap): flash swap WAVAX out of the pair, buy aHEFE on the 314 pool, unwrap, repay the pair
    in HEFE, sell the HEFE left on the pair, pay the wallet in AVAX;
  - wrap direction (HEFE cheap): flash swap HEFE out of the pair, wrap, sell aHEFE on the 314 pool, repay the pair in
    WAVAX, pay the wallet in AVAX.
- The executor reverts unless the wallet is paid at least `minProfit`; the bot sets `minProfit` = that send's gas cap.
  No principal: the pair's flash swap funds it.

## Competition, last 7 days (attempts:3655, scratch/rdf0b/hefe-hist.json)

Every log of the wrapper in avalanche blocks 100,454,105-101,054,105 (the token launched 2026-11-20 05:13Z):

| operator (EOA -> contract) | takes | when | gas price | tx index |
|---|---|---|---|---|
| 0x1375b76a -> 0x7e4111c5 | 98 | 11-20 05:13Z-19:51Z, 43 s apart in the first half hour | 7.5-8.2 gwei | 0-39 |
| 0x58d15e7f -> 0x6ebfb347 | 1 | 11-20 05:19Z | 8.7 gwei | 1 |
| 0x8777ff73 -> 0x60b4401b | 2 | 11-21 03:09Z, 11-21 23:59Z | 10.4, 12.6 gwei | 1, 0 |

- The two takes since 11-20 19:51Z paid 0.0203 and 0.0307 AVAX (0.13 and 0.20 USD at 6.59 USD) for 0.0038 and
  0.0054 AVAX gas (369,502 and 428,062 gas).
- Blocks from the opening trade to the take were not measured (trial: the bot measures it by sending). Priority fees
  are a few gwei over the base fee; the bot bids at most 1/10 of gross, 1-50 gwei.
- Now about one take a day, 0.1-0.2 USD each. This trial is about the win rate, not the money.

## Trigger and read cost

- Feed `/logs/avalanche`, ONE filter: addresses pair `0xe11e871d...` and 314 pool `0x4c726f61...`, topic0
  `Sync(uint112,uint112)` or `Swap(address,uint256,uint256,uint256,uint256,bool)`: about 34 logs a day (22 Sync and
  1 Swap in 16.4 h, scratch/trial-hefe-wrap-avalanche/rate.py). The avalanche feed had 0 filters on 2026-11-22.
- On each log, gap, 429 / 503 or connection error, and every 600 s (safety poll): ONE `eth_call` of the executor's
  `probe()` (28 sizes, both directions). Up to three follow-up looks (4, 15, 45 s) while a gain stands.
- Live Alchemy CU/day: (144 safety polls + 34 feed looks + follow-ups, about 200 calls) x 26 CU = about 5,200 CU,
  plus about 3 reads x 20-26 CU per opportunity and the feed's own CU for 34 small logs: under 6,000 CU/day =
  0.003 USD/day at 1M CU = 0.53 USD. The bot stops reading at 95,000 CU/day and sleeps to 00:00 UTC.

## Limits in the code (bot.py)

- send only when gross > 1.3 x gasLimit x maxFeePerGas; `minProfit` = that cap, so a win always nets more than gas;
- maxFeePerGas <= 200 gwei, gas limit <= 900,000, cap < 0.95 USD at an AVAX price of 20 USD;
- every relay read is inside the loop's handler for the CU cap.

## Files

- `bot.py`, `run.sh`, `executor-runtime.hex` (paper code override = `eth_getCode` of the fork deployment);
- executor source `scratch/trial-hefe-wrap-avalanche/contracts/src/WrapPairArb.sol`;
- proof `scratch/trial-hefe-wrap-avalanche/proof.py` (both directions at the parents of two real takes), `selftest.py`.
- Logs: `logs/bot.jsonl`: `start`, `feed`, `opportunity`, `paper_sim`, `simulate_revert`, `opportunity_skip`,
  `send_result` (won / lost, gas_used, winner_block), `heartbeat`.

## When to stop

- After 7 days live or when the 5 USD is spent: one `attempts` row (sends, wins, net) and the lead set to `measured`
  or back to `blocked_infra`.
- Earlier if the wrapper is paused or emptied, or trading in the token stops (no `opportunity` for 3 days).
