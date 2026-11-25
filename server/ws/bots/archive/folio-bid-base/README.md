# folio-bid-base

Flash-funded bids on Reserve Folio (index DTF) rebalance Dutch auctions on Base. Not a trial bot: the last public
bids are 7.7 days old (2026-11-10), so the 7-day rule of the trial decision is not met; it is a scheduled-window bot
whose occurrences are counted with the seconds race rule (decision 2026-11-14-race-rule-seconds).

## What it does

A Folio rebalance (about monthly per Folio) opens Dutch auctions of 15 min (LCAP) or 30 min (BGCI). In an auction
anyone may call `bid(auctionId, sellToken, buyToken, sellAmount, maxBuyAmount, false, "")`: the Folio hands out its
surplus token and takes its deficit token at a price that only falls (exponential decay, about 0.014 pct/s on the
measured pair). Six public bidders took 59 lots on 2026-11-10; the sampled one waits until a lot nets about
0.0008 ETH. The bot sends as soon as a lot nets 0.0003 ETH (`MIN_NET_WEI`) and 3x the signed gas cap, which was
7-168 s earlier (median 34 s) on the lots that count. This is a threshold contest on a falling price, not a
latency race, and it is the shape the human approved for lead 74 (bid at a lower line than the incumbent).

One transaction through the executor `FolioBidTake` (owner-only `run`):
Morpho WETH flash loan (no fee) -> buy the deficit token on the WETH pool with the most WETH (PancakeSwap V3 or
Uniswap V3, exact output, 0.2 pct more than `getBid` asks) -> `Folio.bid` -> sell the surplus token for WETH -> sell
the unused deficit token back -> repay -> revert `NoProfit` unless native + WETH grew by `minProfit` -> pay the gain
to the bot wallet as native ETH. No principal; the wallet holds gas only.

## Loop and read cost

- Idle: one Multicall `eth_call` per 60 s (`nextAuctionId()` of 6 Folios) = 1,440 calls x 26 CU = **37,440 CU/day =
  0.02 USD/day** (1M CU = 0.53 USD). A timer, not the feed: an auction lasts 900-1800 s and no lot met the line in
  the first minutes of the measured auctions, so a 60 s detection delay costs nothing; the feed would need one
  filter per Folio.
- Open auction: every 6 s one `getBid` Multicall over the biddable pairs (all ordered pairs every 12th tick), one
  `eth_getBlockByNumber`, at most 2 executor simulations (`eth_call`; paper adds the code override): about 98 CU per
  tick, 29,000 CU per 30 min auction, about **150,000 CU on a rebalance day** (5 auctions), about once a month.
- Hard stop at 200,000 CU per UTC day (`RELAY_CU_CAP`). No feed subscription.
- Live adds per send: `eth_estimateGas`, up to 20 receipt polls, one `eth_getLogs` (winner lookup).

## Loss guard

- Executor: `NoProfit` revert unless the balance ends `minProfit` higher (FolioBidTake.sol:60); `minProfit` = this
  send's gas cap, so a bid that lands late on a worse state reverts and costs gas only.
- Gas cap: `gasLimit` <= 1,500,000 and `maxFeePerGas` <= 0.1 gwei: at most 0.00015 ETH (0.27 USD) per send; measured
  bid 682,048 gas x 0.006 gwei = 0.0076 USD. Fixed 0.001 gwei tip, no fee bidding.
- Send only if simulated gain >= max(0.0003 ETH, 3 x gas cap) and > this send's gas cap (bot.py `try_lot`).

## Windows (seconds from takeable to taken), 2026-11-10 rebalances

Method: `scratch/folio-bid-base/selftest.py 100 300000000000000`. For each of the 59 public `AuctionBid` logs the
bot's own functions (`auction_info`, `find_legs`, `get_bids`, `plan_for`, `sim` with the paper code override) are
pinned to historical blocks by relay `eth_call`; a binary search between the previous bid on the same pair (or the
auction start) and the incumbent's parent block gives the first block whose end state met the bot's line
(= takeable). Base ran 0.2 s blocks. Classes: `counts` = taken at least 6 s after takeable (T + R to the farm's
earliest block L, plus R; R = 3 s); `may_try` = 3-6 s; `race` = under 3 s; `below_line_at_parent` = the bot's
route never reached 0.0003 ETH before the incumbent bid; `not_takeable_at_parent` = no working route or no lot.

- 59 bids: **24 counts**, 5 may_try, 4 race, 19 below line, 7 not takeable.
- All 33 with a takeable block: median 19.8 s (99 blocks), minimum -0.2 s (a lot that became takeable in the
  incumbent's own block). The 24 counted: minimum 7.4 s, median 33.8 s, maximum 168.4 s.
- Gain of the 24 counted lots at the takeable block: 0.02281 ETH (41 USD at 1810.43 USD/ETH) if every later lot
  is still offered after an earlier take; 0.00709 ETH (12.8 USD) counting only the first take per token pair per
  auction (18 pairs). With the lower line 0.00012 ETH (`selftest-result.json`): 32 counted, 0.02056 / 0.00362 ETH,
  so the higher line is used.
- Not counted as revenue: the 0.117 ETH the same lots show at the parent block of the incumbents' bids.

Expected value: 12.8-41 USD per rebalance day, about one per month per Folio (BGCI rebalance nonce 16, LCAP 8;
both last on 2026-11-10): **about 0.4-1.4 USD/day** averaged, from one measured rebalance day. The incumbents can
answer by lowering their own line; three lost sends in a row is the signal to stop (as in the lead-74 decision).

| folio | auction | pair (sell > buy) | taken block (tx index) | class | s takeable to taken | blocks | bot gain at takeable (ETH) |
|---|---|---|---|---|---|---|---|
| LCAP | 13 | 0x378c32 > 0x420000 | 55627514 (20) | below_line_at_parent |  |  | 0.000000 |
| LCAP | 13 | 0x378c32 > 0xcb5852 | 55627520 (13) | not_takeable_at_parent |  |  | 0.000000 |
| LCAP | 13 | 0x378c32 > 0x311935 | 55627805 (4) | may_try | 3.6 | 18 | 0.000319 |
| LCAP | 13 | 0x378c32 > 0xcb5852 | 55627856 (6) | below_line_at_parent |  |  | 0.000000 |
| LCAP | 13 | 0x378c32 > 0xcbd06e | 55627874 (5) | below_line_at_parent |  |  | 0.000000 |
| LCAP | 13 | 0x378c32 > 0xcbada7 | 55628019 (6) | not_takeable_at_parent |  |  | 0.000000 |
| LCAP | 13 | 0x378c32 > 0xcbd06e | 55628023 (11) | below_line_at_parent |  |  | 0.000000 |
| LCAP | 13 | 0x378c32 > 0xcbd06e | 55628049 (49) | below_line_at_parent |  |  | 0.000000 |
| LCAP | 13 | 0x378c32 > 0x311935 | 55628135 (2) | counts | 7.6 | 38 | 0.000303 |
| LCAP | 13 | 0x378c32 > 0xcbd06e | 55628173 (3) | below_line_at_parent |  |  | 0.000000 |
| LCAP | 13 | 0x378c32 > 0x311935 | 55628180 (2) | below_line_at_parent |  |  | 0.000000 |
| LCAP | 13 | 0x378c32 > 0xcb5852 | 55628214 (6) | counts | 10.8 | 54 | 0.000861 |
| LCAP | 13 | 0x378c32 > 0xcb5852 | 55628214 (8) | race | -0.2 | -1 | 0.000770 |
| LCAP | 13 | 0x378c32 > 0xcb5852 | 55628329 (16) | below_line_at_parent |  |  | 0.000000 |
| LCAP | 13 | 0x378c32 > 0x15d0e0 | 55628768 (2) | counts | 121.6 | 608 | 0.000508 |
| LCAP | 13 | 0x378c32 > 0xcbb7c0 | 55628815 (11) | may_try | 5.2 | 26 | 0.000489 |
| LCAP | 13 | 0x378c32 > 0x420000 | 55628858 (10) | may_try | 3.8 | 19 | 0.000305 |
| LCAP | 13 | 0x378c32 > 0xcbb7c0 | 55629039 (5) | counts | 30.4 | 152 | 0.000344 |
| BGCI | 86 | 0x9b8df6 > 0x311935 | 55651025 (2) | not_takeable_at_parent |  |  | 0.000000 |
| BGCI | 86 | 0x9b8df6 > 0x311935 | 55651146 (2) | counts | 19.8 | 99 | 0.000374 |
| BGCI | 86 | 0x9b8df6 > 0x311935 | 55651204 (15) | counts | 11.4 | 57 | 0.004483 |
| BGCI | 86 | 0xd403d1 > 0x311935 | 55651314 (5) | below_line_at_parent |  |  | 0.000000 |
| BGCI | 86 | 0x2615a9 > 0x88fb15 | 55651383 (14) | may_try | 4.2 | 21 | 0.000303 |
| BGCI | 86 | 0xa3a34a > 0xcb5852 | 55651502 (8) | below_line_at_parent |  |  | 0.000000 |
| BGCI | 86 | 0x2615a9 > 0x88fb15 | 55651581 (2) | counts | 33.8 | 169 | 0.000341 |
| BGCI | 86 | 0x9b8df6 > 0x88fb15 | 55651589 (41) | counts | 53.4 | 267 | 0.000312 |
| BGCI | 86 | 0x2615a9 > 0x88fb15 | 55651619 (3) | counts | 7.4 | 37 | 0.003350 |
| BGCI | 86 | 0x9b8df6 > 0xcb5852 | 55651634 (37) | counts | 106.4 | 532 | 0.000391 |
| BGCI | 86 | 0x2615a9 > 0xcb5852 | 55651878 (18) | counts | 126.2 | 631 | 0.000451 |
| BGCI | 86 | 0xd403d1 > 0xcb5852 | 55651949 (14) | counts | 140.4 | 702 | 0.000348 |
| BGCI | 86 | 0x2615a9 > 0xcb5852 | 55652018 (22) | counts | 27.8 | 139 | 0.005947 |
| BGCI | 87 | 0x2615a9 > 0xcb5852 | 55660934 (22) | below_line_at_parent |  |  | 0.000000 |
| BGCI | 87 | 0xd403d1 > 0x311935 | 55661058 (16) | counts | 42.2 | 211 | 0.000309 |
| BGCI | 87 | 0x2615a9 > 0x311935 | 55661170 (13) | counts | 102.6 | 513 | 0.000346 |
| BGCI | 87 | 0x2615a9 > 0xcb5852 | 55661250 (17) | counts | 61.6 | 308 | 0.000573 |
| BGCI | 87 | 0x378c32 > 0xcb5852 | 55661485 (30) | not_takeable_at_parent |  |  | 0.000000 |
| BGCI | 87 | 0xd403d1 > 0xcb5852 | 55661710 (2) | counts | 168.4 | 842 | 0.000385 |
| BGCI | 88 | 0xd403d1 > 0x88fb15 | 55671154 (42) | below_line_at_parent |  |  | 0.000000 |
| BGCI | 88 | 0x378c32 > 0x311935 | 55671317 (11) | not_takeable_at_parent |  |  | 0.000000 |
| BGCI | 88 | 0x378c32 > 0x311935 | 55671724 (7) | below_line_at_parent |  |  | 0.000000 |
| BGCI | 88 | 0x378c32 > 0x88fb15 | 55671739 (50) | below_line_at_parent |  |  | 0.000000 |
| BGCI | 88 | 0x378c32 > 0x311935 | 55671803 (2) | counts | 8.2 | 41 | 0.000301 |
| BGCI | 88 | 0x378c32 > 0x311935 | 55671843 (7) | race | 0.6 | 3 | 0.000959 |
| BGCI | 88 | 0x378c32 > 0xcbada7 | 55671881 (22) | not_takeable_at_parent |  |  | 0.000000 |
| BGCI | 88 | 0x378c32 > 0x311935 | 55672000 (4) | counts | 18.2 | 91 | 0.000745 |
| BGCI | 88 | 0x378c32 > 0x311935 | 55672008 (3) | below_line_at_parent |  |  | 0.000000 |
| BGCI | 88 | 0x378c32 > 0x311935 | 55672020 (2) | race | 1.6 | 8 | 0.000817 |
| BGCI | 88 | 0x378c32 > 0x311935 | 55672084 (6) | counts | 10.8 | 54 | 0.000773 |
| BGCI | 88 | 0x378c32 > 0x311935 | 55672109 (3) | below_line_at_parent |  |  | 0.000000 |
| BGCI | 88 | 0x378c32 > 0x311935 | 55672171 (2) | may_try | 4.4 | 22 | 0.000302 |
| BGCI | 88 | 0x378c32 > 0x311935 | 55672189 (10) | race | 1.2 | 6 | 0.000921 |
| BGCI | 88 | 0x378c32 > 0xcb5852 | 55672330 (2) | counts | 97.6 | 488 | 0.000314 |
| BGCI | 89 | 0xcbb7c0 > 0x311935 | 55680253 (156) | counts | 27.2 | 136 | 0.000304 |
| BGCI | 89 | 0xcbb7c0 > 0x311935 | 55680402 (24) | counts | 29.6 | 148 | 0.000422 |
| BGCI | 89 | 0xcbb7c0 > 0xcbada7 | 55680552 (49) | not_takeable_at_parent |  |  | 0.000000 |
| BGCI | 89 | 0xcbb7c0 > 0xcb5852 | 55680672 (2) | counts | 85.0 | 425 | 0.000326 |
| BGCI | 89 | 0xcbb7c0 > 0x311935 | 55680726 (44) | below_line_at_parent |  |  | 0.000000 |
| BGCI | 89 | 0xcbb7c0 > 0x88fb15 | 55680805 (27) | below_line_at_parent |  |  | 0.000000 |
| BGCI | 89 | 0xcbb7c0 > 0xcb5852 | 55681483 (59) | below_line_at_parent |  |  | 0.000000 |

## Evidence and files

- Fork proof: `scratch/folio-bid-base/proof.py 140` -> `proof-result-140.json` (success
  0xb99c2b1e4fb8d9f952bc81f3651946da31d39840bd9f23e47c20ab11bc51b222, owner +0.000670 ETH, 13 s of fork time before
  the incumbent's block 55680402; NoProfit, NotOwner and closed-auction reverts).
- `scratch/folio-bid-base/selftest.py`: bot calldata == the proof's cast calldata; the windows above.
- `scratch/folio-bid-base/smoke.py`: the bot's active path (discover, routes, get_bids, try_lot) with `latest`
  pinned to block 55680380 inside BGCI auction 89: logs `auction_open`, two `opportunity` + `paper_sim` rows
  (0.00070 and 0.00247 ETH), SMOKE OK.
- Addresses: Folios from api.reserve.org/discover/dtf?chainId=8453 (`version()` = 5.0.0, `nextAuctionId()` and
  `auctions()` answer); PancakeSwap V3 SwapRouter 0x1b81D678ffb9C0263b24A97847620C99d213eB14 and Uniswap V3
  SwapRouter02 0x2626664c2603336E57B271c5C0b26F421741e481 are accepted only if `factory()` returns the configured
  factory (checked at every start; the pools come from that factory's `getPool`); Morpho Blue
  0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb (`owner()` answers, 82,967 WETH on hand); Multicall3.
- Live: executor address from `EXECUTOR_ADDR_BASE` or `EXECUTOR_ADDR` only (exit if unset); sends through
  `farmbot_signer` (`my_address()["address"]`).

## Log rows (`logs/bot.jsonl`)

`start`, `auction_open`, `routes`, `below_line` (at most one per lot per 30 s), `opportunity`, `paper_sim`
(paper: would_send), `send` / `send_result` (live: won or lost, gas used, gas cost, the first other bidder's block
on the same pair), `skip`, `no_route`, `simulate_revert`, `signer_reject`, `read_budget`, `loop_error`.

## Limits known today

- One WETH pool per token (the one holding the most WETH); tokens without a PancakeSwap V3 or Uniswap V3 WETH pool
  log `no_route` (7 of 59 historical bids were not takeable through these routes; Aerodrome is not wired).
- Sizes tried: the whole available lot, then a quarter.
- Paper cannot show a natural capture before the next rebalance (expected around 2026-12-10); the smoke test and
  the 59-bid replay stand in for it.
- BSC (CMC20 Folio 0x2f8a339b5889ffac4c5a956787cda593b3c36867, 3.7M USD) is not covered: no bid logs in 1.5M blocks,
  without a same-run control.
