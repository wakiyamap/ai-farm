trial

# trial-folio-nav-bsc

Cheap-chain trial (decision 2026-11-17-cheap-chain-trials). Reserve Folio CMC20 ("CoinMarketCap 20 Index DTF",
0x2f8a339b5889ffac4c5a956787cda593b3c36867, about 3.6M USD, version 5.0.0) on BSC can be redeemed for its basket of
16 tokens by anyone with `Folio.redeem(shares, receiver, assets, minAmountsOut)`. When CMC20 is cheap in one of its
PancakeSwap V3 pools relative to the basket, this round trip pays, in one transaction through the bot's executor:

flash-swap CMC20 out of the pool (CMC20/WBNB 0x4353e8c1... or CMC20/USDT 0xb4bd7ec1..., both fee 0.05 pct) ->
`redeem` inside the swap callback -> sell BTCB, ETH, XRP, SOL, TRX, DOGE, ADA, HYPE, LINK, XLM, BCH, UNI, AVAX, ZEC, LTC
in the pools the incumbent uses (10 V3-style pools, 5 V2 pairs; XRP and ZEC through USDT) -> pay the pool what the
swap owes -> the WBNB gain is unwrapped and paid to the bot wallet as native BNB. The executor reverts `NoProfit`
unless the gain is at least `minProfit`. No principal: the pool hands out the CMC20 first.

Sibling of trial-folio-nav-base (LCAP on Base); own code, own executor (BSC has no Balancer V2 Vault, and five basket
tokens trade best on V2 pairs).

## Honest expectation

The bot will send rarely and is expected to lose nearly every send. It exists to measure that by sending.

- Last 25.0 h (blocks 134,441,131-134,641,131, Transfer from / to 0x0 on CMC20, `scratch/trial-folio-nav-bsc/scan.py`;
  the 7,634 Transfer logs of the same query are its control): 102 public mint / redeem round trips, 81 mints and 21
  redeems. A 7-day scan was not run (BSC log pages cost CU); the day's rate is about 100 takes.
- Who (`stats.py`, `takes.json`): executor 0x742414b7799ed19bbd2d018bbcb6bd66d16594fe 62 (senders 0x031d229e,
  0xceac4024, 0xaeb7596a; entry selector 0xa9059cbb), 0x1836532f67ee5299f41e11d0ee9c80dbb5af34ec 29 (many senders),
  vanity 0x0000000000be226afde21672a5e4adc45692e69d 9, 0x3ee0a37fc6f3857acb155449b632e6776712caea 2 (CMC20/BTCB pool).
- What a take pays (WBNB kept by the executor, from the receipt): redeems gross median 0.000284 BNB (0.16 USD), max
  0.00337 (1.9 USD), 7 of 21 above 0.0005 BNB, sum 0.0122 BNB for 0.0022 BNB of gas; mints gross median 0.00013 BNB,
  sum 0.0142 BNB for 0.0090 BNB of gas. Whole class about 8.5 USD a day net; the redeem side about 5.6.
- Priority fee level: none. Every take pays the 0.05 gwei floor (max seen 0.0501). Gas 1.74M-3.9M, about 0.0001 BNB
  = 0.055 USD per take. Tx index 1-67, median 4 (redeems), 12 (mints). 0x742414b7 fires from about 0.00012 BNB gross.
- Blocks to take (`series.py`, `series-windows.json`): this bot's own `probe()` with a code override at blocks before
  each of the 21 redeem takes (BSC blocks are 0.45 s). A gain above 0.00015 BNB (about one gas cap of this bot) was
  visible at the parent block for 11 of 21, two blocks before for 3, four blocks (1.8 s) before for 0. Smaller gains
  (0.00005-0.0001 BNB, below both the incumbent's and this bot's line) stood 3-30 s on 9 of 21.
- So: a takeable gap stands 0.45-0.9 s and the incumbent takes it in the next block. With a 40 s timer (5 s for a
  minute after any gain shows) the bot sees such a state rarely and then lands several blocks late; it bids up to 20
  pct of gross as gas price, which orders it ahead only inside the same block. Expected: a few sends a week, nearly
  all lost at about 0.06 USD each. Paid entries in the last 7 days whose gross exceeds one attempt's gas: all 21
  redeems (e.g. 0x39a048d7..., block 134,625,965, 0.000719 WBNB against 0.0000966 BNB gas).

## What it does

- Every 40 s one `eth_call` of the executor's `probe()` (both routes: 0.7 WBNB on the WBNB pool, 400 USDT on the USDT
  pool). When a probe shows any gain it looks every 5 s for 60 s, at most once per 20 minutes.
- A gain: sweep the sizes (0.3 / 0.7 / 1.5 / 2.5 WBNB, or 170 / 400 / 850 / 1700 USDT), estimate gas, gas limit =
  estimate x 1.2 + 100,000, gas price = `eth_gasPrice` + a bid of at most 20 pct of gross, cap = gasLimit x gasPrice.
  Send only if the simulated gross is above the cap, with `minProfit = cap + 1`, after simulating the exact call at
  the signed gas limit.
- Paper mode logs `paper_sim`; live mode sends through the signer and logs `send` and `send_result` (won / lost, gas
  used, the winner's block and tx = last swap on either CMC20 pool up to our block).

## Limits

- Signed worst case of a send: gasLimit (at most 3.7M) x gasPrice, refused at 0.90 USD or more at the pool's BNB
  price x 1.15; typical 0.00015-0.0008 BNB = 0.09-0.45 USD.
- Capital 3 USD, all native BNB, no top-up: about 20-50 lost attempts.

## Read cost

Timer 2,160 probes x 26 CU = 56,160 CU a day; bursts at most 72 x 12 x 26 = 22,464; sweeps about 200 CU each. About
60,000-80,000 relay CU a day = 0.03-0.04 USD at 0.53 USD per million; code cap 95,000, then it sleeps to 00:00 UTC.
No feed filter: the two CMC20 pools emit about 1,600 and 3,500 Swap logs a day, a busy event by the feed rules.

## Fork proof and self-test

`python3 scratch/trial-folio-nav-bsc/proof.py 134625964 proof-result.json` and
`python3 scratch/trial-folio-nav-bsc/proof.py 134585927 proof-result-134585927.json` (one BSC fork lease each: reset
to the parent of an incumbent take, deploy, fund, probe, non-owner, guard, success, repeat). Results in the manifest.
`scratch/trial-folio-nav-bsc/selftest.py <block>...` checks the hand ABI encodings against cast, the route table
against the proof's, and replays the bot's own `check()` at past blocks.

## Not built

- The mint direction (buy the basket, `mint`, sell CMC20): 81 of the 102 takes, smaller each (median 0.07 USD gross).
  Needs exact-output buys of 16 tokens in basket proportion and the mint fee.
- The CMC20/BTCB pool (0x7ff63e6c..., 2 takes) and three CMC20 venues that are not V3-style pools.
- A basket change (the Folio rebalances about monthly) needs the route table re-read: a new basket token without a
  step makes every run revert or sweeps that token to the wallet as dust.
