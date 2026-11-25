---
type: mechanism
chains: [ethereum]
protocols: [morpho_blue]
---
# Morpho Blue liquidation markets on Ethereum: what is actually liquidated (census 2026-11-11)

The live farm watcher pins two 6-dec USDC-loan markets (WETH/USDC 0x94b823e6bd8ea533b4e33fbc307faea0b307301bc48763acc4d4aa4def7636cd, WBTC/USDC 0x3a85e619751152991742810df6ec69ce473daef99e28a64ab2340d7b7ccfee49). Over blocks 26325000-26391872 (7 d, 98 blue-pool Liquidate events) those two markets carried 19 events with repaid totals 41,140 + 151,490 USDC (max 23,845 / 92,326 USDC per event) - real mid-size captures. The other 79 events ran on markets with 18-dec loan tokens nobody in the farm watches.

## The active non-pinned markets

Named from the Transfer into Morpho (0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb) matching each market's largest event's repaidAssets at tx level, plus name()/decimals() eth_calls (run 9d3cc38e, attempts:921):

| market id | loan token | 7 d events | repaid (token units, 18-dec) |
|---|---|---|---|
| 0xd2630c0ebf33ba83c82e8cd400a8e6345370238ca695ce58773b2d3e43de1b0a | Metronome "Synth ETH" 0x64351fc9810adad17a690e4e1717df5e7e085160 | 10 | 78.4 SES (~160 k USD-est) |
| 0x0d55c325847ed87d53506c2aca7de046cb59d8c22928fd55fb2790c4811d20db | same sES token | 4 | 354.9 SES (~730 k USD-est) |
| 0xea4bfb18df0ee6bffb7b3f0270899a8adb92ab6b684709634c8276128813cfd4 | RLUSD 0x8292bb45bf1ee4d140127049757c2e0ff06317ed | 1 | 394,691 (one ~395 k USD capture) |
| 0x82053fe2fc3a3d6cb856458948e9c3589e76f20f3a2079606739b517587267ce | "EUR CoinVertible" 0x5f7827fdeb7c20b443265fc2f40845b715385ff2 | 1 | 26,605 EUR |
| 0x4fa31e3f8ba345227d44e1cf48559eea53a90dd5311dc006984c060f2f311d96 | RLUSD | 4 | 6,567 |
| 0x140fe48783fe88d2a52b31705577d917628caaf74ff79865b39d4c2aa6c2fd3c | USDe 0x4c9edd5852cd905f086c759e8383e09bff1e68b3 | 2 | 473 |

At the farm's <= 400 USD repay scale a liquidator only ever repays its own flash-funded slice and keeps the 5 pct penalty on it - slice size does not depend on how big the market is. The case for re-pinning a whale market is therefore cadence (more liquidatable crossings per day), not slice size; 0xd2630c0e... (sES loan) crossed 10 times in 7 d, the most of any single market.

## No market-config getter

Morpho Blue on Ethereum (0xbbbbbb...cb) exposes no getter for the market registry: `idToMarketConfig(bytes32)` 0x7a957e13 and `marketConfig(bytes32)` 0x5f6a8b69 revert on registered ids, and neither selector appears in the 15,624-byte deployed code (control: `owner()` 0x8da5cb5b answers 0xcba28b38103307ec8da98377fff9816c164f9afa). Market configs for a re-pin must come from winner tx inputs and the event's token Transfers - exactly how this census named the loans - not from an eth_call.

## Reading the units

repaidAssets is in loan-token units: for 18-dec loans 6.13e16 = 0.06 RLUSD (dust), not 61 WETH. The 2026-11-11 morning note calling 0x88abdf8693e663144c3544b9442e9b04520016d6ebc57aa76424c00ab1683c9d's capture "61.29 WETH ~ 126 k USD" (attempts:913) misread the loan decimals: it is a 6-cent dust repayment (corrected by the transfer-value match, attempts:921).
