# blur-refi-taker-ethereum

Takes Blur Blend Dutch **refinance auctions** on Ethereum. When a borrower wants
to refinance a lien, Blend (`0x29469395eAf6f95920E59F858042f0e28D98a20B`) opens a
9000-block Dutch auction whose **rate ceiling grows monotonically** from ~0 as
`startSlope × blocks-since-auctionStartBlock` (measured ~3.215 bips/block for the
winner's oldRate 2930 / duration 9000; `Helpers.calcRefinancingAuctionRate`).
`refinanceAuction` is **anyone-callable**: any bidder whose rate stays under the
ceiling takes the lien and Blend pulls the debt from the bidder's Blur Pool
balance (a 1:1 native-ETH accounting token) to the old lender. We fund a 0.19 ETH
Pool-unit float in the executor, take with `take()`, and after the borrower
repays the new lien, `sweep()` withdraws Pool units and returns principal plus
accrued interest as **native to the bot wallet** (fork-proven positive delta).

## Census and windows (decision 2026-11-12 item 2: no same-block races)

30-day census, 221 `StartAuction` / 220 `Refinance` fills (attempt 954, raw logs
in `scratch/blend-logs/`, head 26394752). Blocks from eligible (auction start)
to taken (fill):

| stat | value |
|---|---|
| fills | 220 |
| median window | 1903 blocks (~380 min) |
| p10 window | 317 blocks (~63 min) |
| minimum window | 2 blocks (1 of 220 fills; the only same-block-class race, kept out of EV) |
| maximum | ≈ auction duration (9000 blocks) |

Poll-compatible windows are the rule — a 15 s poller catches a >300-block p10 with
enormous margin; the incumbent is not racing (the winner took lien 446638 47
blocks after the start at rate 147, tx
`0x9ed2ebfdf9f48b84f1eac8179adcd8a65f71240ccaae30f240e6f05e4af2805a`).

## Economics

~7.4 starts/day, ~23 fills/day at our 0.13 ETH lien cap, gross 1.13 USD/day,
gas ~0.14 USD/fill. Reads: ~0.15M Alchemy CU/day (~0.08 USD) at 15 s polling of
`StartAuction(uint256,address)` / `Refinance(uint256,address,address,uint256,uint256,uint256)`
topic0s on Blend.

## Executor

`contracts/src/BlurRefiTaker.sol` (solc 0.8.17 pinned — solc 0.8.24 flattens the
tuple-form `refinanceAuction` selector to `0xcf5da407` and Blend reverts):
`receive()` mints funded native 1:1 into Pool units (gated `withdrawing` so
sweep's own payout is not re-minted), `take()` pays the reconstructed debt cap
through Blend, `sweep()` withdraws and pays the wallet, reverting unless profit
≥ minProfit. Paper sim uses `executor-runtime.hex` (2945 bytes, `eth_getCode` of
the fork executor; re-take after **every** source change — source sha
`e35df7a5`).

## Fork proof

`scratch/blur-proof.sh` (reruns green, run e80ea7d3): the full route — fund
0.19 ETH via receive (mint 1:1 proof), take lien 446638 at the winner block state
(Pool debit 185896784673149155 = the winner's debt within seconds of accrued
interest), five guard reverts, sweep with the float preserved and a **positive**
wallet delta +80690127848445 wei. Reset 26389938 (winner block − 1): the Dutch
ceiling at elapsed < 47 blocks is below 147, so a proof at the auction-start
block reverts `RateTooHigh` by design.
