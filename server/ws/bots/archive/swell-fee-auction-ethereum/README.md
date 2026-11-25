# swell-fee-auction-ethereum

Buys Swell's fee auction in one flash-funded transaction when a large fee mint makes the pot worth more than its price.
Lead 359, attempts:3267, wiki `mechanisms/swell-fee-auction.md`. Not a trial bot (ethereum); private send.

## Mechanism

- Auction `0xf17b581496bc2669ce0931facaa1ade35029e85d`: a `FeeFlowController` (euler-xyz/fee-flow interface). `buy()` pays
  `getPrice()` SWELL (burned) and receives the auction's whole swETH + rswETH balance. The price falls linearly to 0 over
  14 days; after a buy the next epoch starts at max(2 x paid, 4,000,000 SWELL). Open to anyone (fresh-address `eth_call`
  passes every check up to the SWELL pull; wrong epoch reverts `EpochIdMismatch`).
- Swell's reprice transactions mint swETH / rswETH fees to the auction. When one large mint lands, the pot is worth more
  than the current price and whoever buys first keeps the difference.
- Executor `FeeAuctionBuy.run()`: Morpho Blue flash WETH -> unwrap -> Universal Router V4 exact-output swap for exactly
  `getPrice()` SWELL (unused ETH swept back) -> `buy([rswETH, swETH])` -> swETH sold either through the router (V4 exact
  input) or on the Uniswap V3 0.05 % pool `0x30ea22c8...` through SwapRouter02; rswETH -> weETH -> WETH on two Curve-style
  pools -> wrap, repay -> revert unless WETH left >= `minProfit` -> profit unwrapped and sent to the owner as native.
  All addresses and routes are arguments. The bot simulates both swETH routes and sends the better one: at the
  swETH-only event (block 26224357) the v4 pool could not take the size and only the V3 route worked.

## What the bot does

1. Waits on farm-feed: `/logs/ethereum`, addresses swETH `0xf951e335...` and rswETH `0xfae103dc...`, topic0 `Transfer`,
   topic1 = `0x0` (mints only); it reacts when topic2 is the auction. Safety poll of the state every 300 s; on `gap`,
   429, 503 or a connection error it sleeps to the end of the 300 s interval and re-reads the state through the relay.
2. Reads `getPrice()`, `getSlot0()` and the auction's two balances; when the pot is not empty it simulates `run()` with
   `eth_call` (paper: the fork-proven runtime as a code override). `run()` returns the profit.
3. Sends (live) or logs `paper_sim` (paper) only when the simulation succeeds, i.e. profit >= `minProfit` =
   gas cap (1,200,000 gas x 5 gwei = 0.006 ETH) + 0.002 ETH, and base fee + 2 gwei priority <= 5 gwei.
   Deadline block = head + 3; no receipt after that is logged as `private_not_included`.

## Past occurrences (60 days to block 26,462,708; scratch/enz-391e/swell-buys.json, swell-inflows.json)

| mint block (UTC) | what was minted | bought in | seconds / blocks from takeable to taken | buyer tx index, gas price | buyer kept |
|---|---|---|---|---|---|
| 26081572 (09-29 07:16) | 2.44745 rswETH | 26081573 | 12 s / 1 | 100, 0.94 gwei | 1.170094 WETH |
| 26224357 (10-19 04:53) | 0.67064 swETH | 26224358 | 12 s / 1 | 0, 0.14 gwei | 323.66 USDT (this bot's code: 0.134 WETH) |
| 26376821 (11-09 10:45) | 0.2286 swETH + 0.1759 rswETH | 26376822 | 12 s / 1 | 27 | about 12-22 USD (this bot's code: 0.0074 WETH, under its minProfit, not sent) |

Median and minimum window: 12 s / 1 block. Under decision `2026-11-14-race-rule-seconds` (ethereum R = 12 s) the buy sits in
the farm's earliest block, so the bot may try these but they are **not counted** as expected revenue. Counted EV: 0.
Uncounted: about 2,250 USD in 60 days if every lump were won. The other 4 buys in the window were decay buys (the price
fell to the pot value, 243-623 USD pots) that kept about gas (last: +0.52 USDT for 0.35 USD gas); the bot's `minProfit`
keeps it out of those.

Since 2026-10-21 Swell's 6-hourly bot has not minted to the auction; the two inflows since came through a Safe
(11-09, 11-13). Timing is irregular. If nothing is minted to the auction for 30 days, stop the bot and close lead 359.

## Proof

- Fork: `scratch/swell-auction-ethereum/proof.py` -> `proof-result.json`: success at the 26081572 state, owner
  +1.169631 ETH after gas (tx `0x7681c9aa...82c0`, gas 784,790); guards NotOwner, Late, NoProfit; nothing-to-take
  revert at the 26081571 state; at the 26224357 state the v4 route reverts `RouterFailed(2)` and the V3 route
  succeeds with +0.133871 ETH (tx `0xe2b6864d...888f`, gas 507,054).
- Bot path: `scratch/swell-auction-ethereum/paper_path_test.py`: this bot's calldata and code override through the
  relay at the historic blocks: 26081572 -> 1.170080 / 1.170131 WETH (v4 / V3 route); 26081571 -> revert;
  26224357 -> v4 revert, V3 0.133901 WETH; 26376821 -> NoProfit 0.0074 WETH (below `minProfit` 0.008, not sent).
- Encoder: `scratch/swell-auction-ethereum/mk_bot_files.py` compares `run_calldata()` with `cast calldata` for both routes (equal) and
  the selectors with `cast sig`. `templates.json` holds the two Universal Router calldatas of tx `0x27fbe89a...e26b`; the
  bot replaces the deadline, the ETH maximum and the sweep recipient, the executor overwrites the amount words on-chain.

## Read cost

- Relay: state read every 300 s = 4 `eth_call` x 26 CU x 288 = about 30,000 CU a day; while a pot sits below the price,
  up to two simulations + `eth_blockNumber` per poll add up to about 18,000 CU a day.
- Feed: mints of swETH / rswETH are a few dozen logs a day (about 35 CU each) plus 3-4 CU a minute for the
  subscription = about 7,000 CU a day.
- Total about 45,000 CU a day = 0.02 USD a day at 1M CU = 0.53 USD.

## Limits

- Worst case per transaction: 1,200,000 gas x 5 gwei = 0.006 ETH (about 10 USD); `max_loss_per_tx_usd` 20.
- If the ethereum feed has no free filter slot (429), the bot only polls every 300 s and would be late for a lump:
  `feed_err` rows on every cycle are the sign.
- The executor leaves no value behind: WETH and native are 0 after the proof transaction.
