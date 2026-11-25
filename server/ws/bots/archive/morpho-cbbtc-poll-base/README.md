# morpho-cbbtc-poll-base (lead 21, base)

Base Morpho cbBTC/USDC pond (`0x9103c3b4...1836`, loan USDC, collateral cbBTC, oracle wrapper
`0x663becd1..39b9`, lltv 0.860 = deployed `0x0BEF55718AD60000` - NOT 0.859: the 1e18-scaled
858993459266134016 from the older probe is wrong and Morpho reverts "market not created").

## Route and windows (measured, `scratch/retriage-1267/`)

12 captures in one cascade block 56677288 (tx `0x4812fa9f9bce933fb5e38edd8667e629b3e7df0aea8563436dcb65a65c1f8b46`,
11 batched liquidations; ledger `morpho_blue_liquidate`): 4 counted (window >= 2 blocks) with
`window_blocks = 916` (183.2 s at 0.2 s blocks, hf_B1 ~= 0.99999 - the bleed captures crossed the
liquidation threshold by ~0.01 USD of debt before the price update landed in the capture block);
8 window-1 same-block captures (out of EV). Counted-occurrence gross proxy = 0.1628 x repaid
(oracle-implied; realized venue-swap gross must be re-measured - oracle-vs-pool sizing pitfall):

| borrower (counted) | repaid USDC | window | gross proxy USD | gas USD (1.3M x 1 gwei) | net USD |
|---|---|---|---|---|---|
| 0x3af516c5...ca31f | 23,069.74 | 916 blk / 183 s | 3,756.75 | ~0.13 | ~3,756 |
| 0x55c0b426...b610 | 1,362.28 | 916 blk / 183 s | 221.78 | ~0.13 | ~222 |
| 0x26f54b69...5ac3 | 706.82 | 916 blk / 183 s | 115.06 | ~0.13 | ~115 |
| 0x83700ff4...fa19 | 475.73 | 916 blk / 183 s | 77.45 | ~0.13 | ~77 |

1 counted cascade event in 16.5 d of ledger - never extrapolate per-day EV from it; the paper bot
counts gross-gas per capture in `logs/detections.jsonl` (sim delta) and the reviewer recomputes EV
from the table before promotion. Small earlier bleed captures (blocks 56523299-56528249, windows
35-360 s) paid only 0.01-25 USD repaid each (gross <= 4.2 USD) - the same table format applies.

## CU/day

safety scan 2/min x (1 head + 1 market + 7 position reads) ~= 9 reads per scan, feed long-poll
free: ~13k reads/day, well below the 1M CU/day (~0.53 USD) human line. Feed filter: the two pinned
cbBTC/USD aggregators, topic0 `AnswerUpdated` (`0xd76dd1d6a3c4836cc1488f4f24f88a2c833b6c7e2e2b530f037e62796ff593a8`...
build-time pinned; wrapper `0x663b..39b9` emits no events - price updates come from the aggregators
only, and the bot re-reads by relay on gap/429/503 + keeps the 30 s safety poll (the eligibility
crossings happen via interest between updates, so the poll - not the feed - is the primary trigger).

## Fork-proof status (reviewer: rerun `bash scratch/morpho-cbbtc-poll/proof.sh`)

deploy + owner funding + scan + guard proven on the shared fork; the positive-delta liquidate is
open: every pond capture sat ~1 cent USD from the threshold, so the proof must reset exactly on the
borrower's crossing block (`probe.js` prints the scan per reset block). The incumbent batcher won
the whole cascade in the capture block (price-drop batch), so a 30 s poller only beats it on
positions whose crossing started earlier - which is exactly the counted-occurrence definition.
