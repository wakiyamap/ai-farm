trial: ERN below-par redemption on Ethos Reserve (OP Mainnet). Measures the farm's win rate by sending; it does not earn (whole pot about 0.13 USD/day).

## Mechanism

ERN (0xc5b001dc...) trades below 1 USD on the Velodrome ERN/USDC pool 0x605cce50.... Ethos Reserve (a Liquity fork) lets anyone redeem ERN at par for WETH through `TroveManager.redeemCollateral` (0x75c72f45..., no role). One executor call:

1. Balancer V2 flash loan of 5-40 USDC (0 fee).
2. Buy ERN on the Velodrome pool.
3. `redeemCollateral(WETH, ern, trove, trove, trove, nicr, 20, 1e18)`; the NICR hint is computed on-chain.
4. Sell the WETH for USDC on Uniswap V3 0.05% (SwapRouter02).
5. Repay; revert `NoProfit` unless the USDC balance grew by `minProfit`; pay the gain to the bot wallet as USDC.

## Competition, last 7 days (blocks 159,422,043-159,725,031)

- 31 redemptions (4.4 per day), all WETH collateral, all on trove 0xe2a25773....
- 0x6ce08b79f97a96cd843035b3d909f1b0853ee5fc: 21 takes (router 0x9873df52...). 0x67f51077ed4923ece0c1d461afbe19146ae03870: 10 takes (router 0x69f1844f...).
- Sizes 15, 20 or 25 USDC; net 0.023-0.033 USDC per take; gas 790k-922k at about 0.001 gwei plus L1 fee = 0.0015-0.0019 USD.
- Transaction index 1-177 (not a first-block job); priority fee 1,000,000 wei (0.001 gwei), measured on 0x33f6f2be....
- The incumbents wait for about 0.02 USDC: 0x6ce08b79's calldata carries a minimum profit of 22,085 micro-USDC, and the gain one block before each of the 31 takes was 18,921-62,734 micro-USDC (15 USDC size).
- Blocks from takeable to taken, at this bot's lower threshold (best of the 5 and 15 USDC simulations >= 4,000 micro-USDC, sampled 1 / 15 / 30 / 90 / 300 / 900 / 1800 blocks before each take; `scratch/trial-ethos-redeem-optimism/windows.py`, `windows.json`): median 15 blocks (30 s), minimum 1 block. 17 of 31 were takeable at least 30 s earlier, 14 at least 60 s, 10 at least 3 min, 3 at least 10 min, 2 at least 60 min. In the other 14 the gain appeared in the last 30 s and the incumbent took it within 1-15 blocks.
- So this is mostly a threshold contest: the bot takes a smaller gain earlier (0.004-0.02 USDC) instead of racing for the 0.02+ one.

## Bot

- Waits on the feed for `Sync(uint256,uint256)` on the pool (372 a day) and checks every 120 s.
- Check: lowest WETH trove (`sortedTroves.getLast`), a 5 USDC probe simulation, then sizes 10-40 USDC; best gain wins.
- Sends only when gross > signed gas cap (`gasLimit x maxFee + 1e11 wei` L1 allowance), `minProfit = cap + 1`.
- Tip: 2,000,000 wei per gas (twice the incumbents), never above 15% of gross.
- Logs: `check`, `opportunity`, `opportunity_skip`, `paper_sim`, `send`, `send_result` (won / lost, gas used, winner block) in `logs/bot.jsonl`.

## Read cost

About 60-85k relay CU/day (cap 80,000 in code), 0.04 USD/day at 0.53 USD per million CU. One feed filter.

## Evidence

`scratch/trial-ethos-redeem-optimism/`: `proof.py` + `proof-result.json` (fork), `selftest.py` (the bot's check at fixed blocks), `tm-logs-7d.json` (7-day events), `trace-33f6.json` (incumbent's trace).
