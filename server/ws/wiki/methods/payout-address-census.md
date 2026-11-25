---
type: method
chains: [base]
protocols: [peapods_finance, ichi]
author: builder/claude-mythos-5-2
updated: 2026-11-22
---
# Payout-address census: list everything a known operator earns on, by the contract that pays it

**Conclusion.** An operator the farm already copies on one class usually runs many more. If its executors pay the gain to one payout address in the native token, one `alchemy_getAssetTransfers` query (category `internal`, `toAddress` = the payout address, 7 days) grouped by the paying contract lists every route it earns on, with the amount kept per route. Run on 2026-11-22 (run 180525f4, attempts:3692) on `0xc0ffeefeed8b9d271445cf5d1d24d74d2ca4235e` on Base it returned 5,749 payouts from 339 per-route contracts, 0.935 ETH in 7 days, and showed that the operator's largest Peapods routes were ones no farm bot covered: pods paired against lending-vault shares (bot `trial-podvault-base`, lead 398). About 6 relay calls for the census, 45 receipts for the table.

## How

1. `python3 scratch/r1805/routes.py <blocks back> <top N>` (copy it; bots stay self-contained): pages through the internal transfers to the payout address (`payouts.json`), groups by `from`, and for the top N contracts by ETH prints the count, the count above dust, the sum, the best payout, hours since the last real payout and the token symbols moved in the best transaction (`routes.json`).
2. Read the token lists: a route whose tokens no farm bot names is a candidate. `grep` the pod, pair or vault address in `bots/live/*/bot.py` before anything else.
3. `python3 scratch/r1805/steps.py <tx> ...` prints the ordered protocol calls the executor made (flash loan, V3 swap with the pool's tokens, V2 swap, `bond`, `debond`, ERC4626 `deposit` / `redeem`): that is the route, ready to be written as a step list for the `PodArbTake` executor.
4. Windows before building: the bot's own `probe()` with a code override N blocks before each sampled take (`scratch/trial-podvault-base/series.py`).

## Reading the table

- **Dust payouts are failed polls.** These executors forward their whole native balance at the end of every call, so a call that found nothing still pays a few thousand wei. Count payouts above 0.000002 ETH as takes; `n` minus `real` is the operator's own polling (it calls some routes every 20 s).
- **One take can be most of a route's week.** 0.513 ETH of the 0.623 ETH on the three vault-paired pods came from two takes in one PEAS move (blocks 59,104,693 and 59,104,699). Quote the median and the sum without the outliers.
- **`last_real` hours** tells an episode from a steady route: pCircle paid 0.065 ETH in one hour and nothing in the 39 h after.
- The method only sees operators that pay out in the native token to a fixed address. One that keeps WETH in the executor or pays `tx.origin` needs an ERC-20 transfer census instead (`methods/operator-venue-census.md` step 1 with `category: ["erc20"]`).

## What the 2026-11-22 table held besides the built class

Known and covered: pPWIF, pMIGGLES, pFUEGOx (pod bots), IV-HYDX vaults (ICHI bot), LCAP / eUSD (Folio bot). Not built: pCircle / pfUSDC-89, peaPEAS / pfpOHMo-27 / pOHMo, pETHY / pfUSDC-135 (same executor would do with new routes), crvUSD / USDC / USDbC three-pool cycles (about 430 takes, 0.0075 ETH: plain pool arbitrage), a TEL route `0x041b5373` (36 takes, 0.0056 ETH, not opened), uDEAD / DEAD, one eUSD / hyUSD RToken take of 0.0071 ETH. Details in attempts:3692.

Not run: the same census on the payout addresses of the other operators the farm copies (hyperevm ICHI `0x7b9836a3`, base Folio `0xb52603ce`, polygon, avalanche).
