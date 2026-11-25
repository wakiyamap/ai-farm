trial

# trial-hbhype-redeem-hyperevm

hbHYPE (`0x96c6cbb6251ee1c257b2162ca0f39aa5fa44b1fb`, Hyperbeat / Upshift vault, withdrawal-only) redeems in one
call, `requestRedeem(shares, receiver, holder)`, at `convertToAssets` = 1.0322144 WHYPE a share, no fee, no wait
(`withdrawalFee()` 0, `withdrawalsPaused()` 0, the vault itself holds all 19,856 WHYPE; 2026-11-21 16:45Z). It also
trades on four thin V3-style WHYPE pools. When somebody sells hbHYPE there instead of redeeming, the pools fall under
the redemption value; this bot buys it back and redeems in the same transaction.

One transaction through the `RedeemArb` executor: nested flash swaps on every pool below value (each pool stops at
its own price limit = redemption value less the pool fee), one redemption of all shares, every pool paid from the
redemption, the rest unwrapped and sent to the bot wallet. No principal. It reverts unless it gained at least
`minProfit`, which the bot sets to the send's gas cap.

## Competition, last 8 days (700,000 blocks to 51,872,631; `scratch/ra22b/hb-scan.json`, `hb_pool.py`)

One burst. Sales: block 51,286,953 (liquidator `0x5ac9bc14`, 11.4 hbHYPE, pools 2.1-2.8 pct under value), 51,287,378
(4.9 hbHYPE), 51,320,910 (0.93).

| taker | txs | blocks | kept (WHYPE) | gas price |
|---|---|---|---|---|
| A: EOA `0x4d396974` via `0x822b3b26` | 5 | 51,286,965 / 977 / 51,287,024 / 51,287,390 / 51,380,628 | 0.0283, 0.0247, 0.0209, 0.0284, 0.0298 | 0.10-0.98 gwei |
| B: EOA `0x4021cf3f` via `0xb42dd31b` | 2 | 51,286,957 / 51,287,380 | 0.0040, 0.0025 | 0.12 gwei |
| `0x609c8738` (contract creation) | 1 | 51,423,413 | not measured | 0.11 gwei |

- Blocks from sale to first take: 4 (B, block 51,286,957), then 12 (A). No priority-fee bidding (0.10-0.12 gwei).
- The takers use small fixed sizes (0.2 and 1.5 WHYPE), so the gap closes slowly: 1.3-1.5 pct still open 71 blocks
  after the first sale; about 1.0 pct open on all four pools from block 51,287,391 to 51,380,628 = 93,237 blocks
  (about 26 hours), closed by A in one tx (+0.0298 WHYPE). This bot's take at that parent block: 0.0305 WHYPE.
- Total kept by redeemers: about 0.14 WHYPE = 8.4 USD at HYPE 60.40 USD. Routers took a further part by cycling
  between the pools.
- Since then only dips of 0.1-0.3 pct (blocks 51,829,114 and 51,853,347): 0.00098 HYPE takeable at head 16:50Z.

## How it decides

Every 35 s one Multicall3 `eth_call`: `convertToAssets(1e18)`, `withdrawalFee()`, `withdrawalsPaused()`, `slot0()` of
the four pools. A pool counts when its price after fee is more than 0.03 pct under the redemption value. Then one
`eth_call` of `take()` gives the exact gain; below 0.0005 HYPE nothing happens (and the same prices are not simulated
twice). Above: base fee, `eth_estimateGas`, tip = at most 1/10 of gross over the gas limit (max 2 gwei), cap =
gas limit x max fee; it sends only when gross > 1.3 x cap, with `minProfit` = cap. Paper mode logs `paper_sim` and
sends nothing.

## Loss bound

Gas only: at most 1,400,000 gas x 7 gwei = 0.0098 HYPE (0.59 USD at 60.40) a send; typical cap 0.00025 HYPE.

## Read cost

86,400 / 35 = 2,469 looks x 26 CU = 64,200 CU/day, plus about 110 CU per opportunity; cap in code 95,000 CU/day.
At 1M CU = 0.53 USD: about 0.035 USD/day. No feed filter (a timer; the gap stands for minutes to hours).

## Logs (`logs/bot.jsonl`)

`start`, `heartbeat`, `check` (below interest), `opportunity`, `opportunity_skip`, `simulate_revert`, `paper_sim`,
`send_result` (won / lost, gas used, send block, winner's block = newest vault `WithdrawalProcessed`), `read_budget`.

## Proof

`scratch/trial-hbhype-redeem-hyperevm/proof.py` (head fork with real transactions + relay `eth_call` at the
incumbent's historical block; the hyperevm fork cannot replay old state), `selftest.py`. Numbers in the manifest.
