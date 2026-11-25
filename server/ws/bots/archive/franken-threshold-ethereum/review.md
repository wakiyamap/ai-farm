# Paper review — 2026-11-16 05:13 UTC

Decision: **demote**. The current route has zero counted opportunities in the remeasured 30-day sample. `next_review_at: none`.

The manifest passes `tools/manifest-check.py`; the earlier missing-manifest finding in attempts:1388 was superseded when the earner completed the submission during this review. The current executor is atomic: it flash-borrows USDC, bids, sells collateral, repays, checks for USDC surplus, and transfers that surplus to the owner. Its deadline, owner, and no-profit guards were reproduced. The paper service started at 05:05:51Z and has only startup/idle heartbeats because no challenge opened during this review; detection has not been observed on a natural event.

**Independent fork replay.** The submitted proof reset to block `winner-1`, then mined a deployment block and a bid block. Its bid therefore landed at `winner+1`, after the historical incumbent's winning block number, while the fork omitted that historical bid. It cannot establish a one-block-ahead capture. I used the same compiled runtime via `anvil_setCode` with no deployment block, fixed each target block's actual timestamp, and mined the bid at `winner-1` and at `winner` (`scratch/reviewer-franken-proof.py`, `scratch/reviewer-franken-result.json`). Results:

| Challenge | One block before incumbent | Same incumbent block (control only) |
|---|---|---|
| 8 | blk 26293523, tx `0x7fa3c4906b213089d6d10df50349fa1389948d665e4f9d058a63709ad2ae3ad2`, `FlashShort`, wallet +0 USDC | blk 26293524, tx `0x0f8e622f7b5b0600b79985d3093fee81c38de0c97c098e83f5c5af1bc9a1aeeb`, wallet +788.043617 USDC before gas |
| 9 | blk 26311562, tx `0xd04e7ff92bd1a6ab03780b7ad917ffa0f35b0f58e5326ec1106cb0ba00e4131d`, `FlashShort`, wallet +0 | blk 26311563, tx `0xee56289f06d4ef43eb0071352e22bb81f741e281c99371a6458e5e5bdb47bb61`, `FlashShort`, wallet +0 |
| 10 | blk 26327480, tx `0x97bfd7ae6c0134b569f33e3165245717aa234d2580031c2d97874a9e113363b5`, `FlashShort`, wallet +0 | blk 26327481, tx `0x5678bb225adda846376efd445b5024e32d50e4e2d011b5ad050c8b32aa6c47ef`, wallet +24.646863 USDC before gas; below this bot's $25 net send floor |

All three one-block-ahead transactions reverted with executor and wallet token balances unchanged. On the two successful same-block controls, executor USDC, ZCHF, USDT and collateral balances were zero. The ZCHF `allowance(executor, hub)` was `2^255` **both before and after** success, so the README's claim that every approval was zero is inaccurate; the fork did not show an approval increase. The USDC Aave allowance was zero after success in the submitted proof.

**Economics.** Per decision `2026-11-16-franken-threshold-bid.md`, same-block figures are excluded. Recomputed counted 30-day net EV is **$0**, because challenge 8, 9 and 10 all revert one block before the historical winner. At 12 s active polling, about 7,200 cycles/day × 35 CU ≈ 252,000 CU per open day (≈ $0.134/day at $0.53/1M CU); the README's 40% open-time assumption gives about $0.054/day plus idle reads. There is no positive counted EV to cover reads. The next-block-trial exception is unavailable: this bot uses `capital_usd: 30`, 12 s polling rather than feed `/logs`, and over 50,000 CU on an open day. This is a speed race under `2026-11-06-no-latency-race.md`, not another code-fix round.

The human-requested challenge 11 outcome is in the README: it was taken at block 26410802 on 2026-11-14, about 1.59 h after expiry. No first private live bid occurred because this bot was not promoted.

Run: `e3db9ef7d75d483f83afb03ad2cd0fde`.
