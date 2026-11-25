trial

# trial-aeb-migrate-avalanche

Trial bot (decision 2026-11-17-cheap-chain-trials): arbitrage of the old 2020 Avalanche bridge tokens against their
`.e` successors.

## Mechanism

Every `.e` bridge token on Avalanche (verified source `BridgeToken`, e.g. USDT.e
`0xc7198437980c041c805a1edcba50c1ce5db95118`) has a public `swap(address token, uint256 amount)`: it burns the old
bridge token from the caller and mints the `.e` token 1:1, up to `swapSupply(token)`. The old tokens still sit in old
V2 pools against WAVAX. Nobody can mint the old token, so an old pool only ever moves one way: when AVAX falls below
an old pool's price, selling WAVAX into it, migrating and buying WAVAX back on the `.e` pool pays the difference.

The executor `MigrateArb` does it in one transaction: V2 flash swap of WAVAX out of the `.e` pair, sell part of it for
the old token on the old pair, `swap()` it 1:1 into the `.e` token, pay the flash pair, unwrap the rest and pay it to
the bot wallet as AVAX. It reverts `NoProfit` unless the wallet is paid at least `minProfit`.

## Competition, last 4.6 days (blocks 100,591,592-100,991,592; `scratch/r6667/aeb_scan.py`, `aeb-txs.json`)

Topic-only `eth_getLogs` of the `.e` token's `Swap` event (topic0 `0x562c2195...004f`, read from a receipt), 0 error
pages: 56 takes, all between block 100,875,860 (2026-11-20 12:22Z) and 100,950,663 (11-21 06:12Z); USDT 38, DAI 18.

| operator | takes | kept (WAVAX) | gas (AVAX) | how |
|---|---|---|---|---|
| executor `0xd1f6ca075b345c3532ee3957f0a32a0a0c881449`, EOAs `0x644e5b7c..` 19, `0xaee4b193..` 14, `0xd312427b..` 7 | 40 | 1.356 | 0.402 | V2 flash swap from the `.e` pair, selector `0x9324b8c2` |
| executor `0x777e0fc6d730cc42b853dc66e9fa1d8700000000`, at least eight `0x777...` EOAs | 16 | not measured | 0.228 | mostly larger sizes (80-150 USDT), selector `0xfdfe738f` |

- Per take: kept median 0.0135 WAVAX (0.09 USD at 6.63 USD per AVAX), range 0.0022-0.371; gas median 0.0046 AVAX.
- Priority-fee level: 8.5 gwei effective in quiet blocks (base fee 7.6 gwei + about 1 gwei), tx index 0-10; in the
  burst of 11-21 (blocks 100,939,679-100,939,765) 60-440 gwei.
- Blocks to take (`aeb_windows.py`, exact V2 math on `getReserves` at N-1 ... N-300 for 13 two-pool takes): a positive
  gain stood 20-80 s before the take in 12 of 13 and more than 200 s in 9 of 13 (take `0x5b110b14...`: 0.0113 WAVAX
  available for 226 s, taken at 0.0075). The incumbents wait until the gain is about 3-4 x their gas: a threshold
  contest, not a first-block race.
- 31 days (`aeb_hist.py`, 3,200,000 blocks): 199 migrations on 15 days; WBTC.e and WETH.e in late October and early
  November, USDT.e on 11-14 (39) and 11-20/21, DAI.e on 11-20/21.

Share aimed at: the first slice of each burst, by sending at 1.3 x the bot's gas cap (about 0.0045 AVAX of gross at
7.6 gwei) where the incumbents wait for 0.0075-0.009. Honest expectation: 0.1-0.5 USD a day on burst days.

## What the bot does

- Every 40 s: ONE `eth_call` (Multicall3 `aggregate3`) reads `getReserves()` of 21 pairs and `swapSupply()` of six
  tokens. Exact V2 integer math off-chain gives the best size per (old pair, `.e` pair).
- Calculated gain >= 0.002 AVAX: `probe()` (eth_call) of the top four candidates, base fee, `eth_estimateGas`,
  gas limit = estimate x 1.1, tip = at most 10 pct of gross (1-3 gwei), cap = gas limit x (base fee x 1.125 + tip).
- Send only when gross > 1.3 x cap, cap < 0.95 USD (AVAX at the Trader Joe pool price x 1.15), gas limit <= 600,000,
  max fee <= 60 gwei, and the exact call with `minProfit = cap` simulates above cap.
- Paper: logs `paper_sim`. Live: sends through the signer and logs `send_result` with won / lost, gas used, the
  tx index and the winner's block (newest `.e` `Swap` event near the send).

## Addresses (each read on chain)

- Old / `.e` tokens: USDT and DAI from the incumbents' receipts; ETH, WBTC, LINK, AAVE accepted because `symbol()`
  answers and `new.swapSupply(old) > 0` (only the bridge role can register a swap token). Supplies at 15:51Z: USDT
  326,793, DAI 109,442, ETH 374.9, WBTC 0.96, LINK 2,795, AAVE 47.3.
- Pairs: `getPair(token, WAVAX)` on the four factories read from `factory()` of pairs in the incumbents' receipts
  (Pangolin `0xefa94de7..`, Trader Joe `0x9ad6c38b..`, `0x5c02e78a..`, `0xc7e37a28..`); `scratch/r6667/aeb-state.json`.
- Multicall3 `0xca11bde05977b3631167028862be2a173976ca11`: answers `aggregate3` (selftest).

## Read cost

2,160 looks a day x 26 CU = 56,160 CU a day = 0.03 USD a day at 0.53 USD per 1M CU. A look that sees a gain adds
92 CU. Code cap 95,000 CU/day; every read is inside the loop's handler that sleeps to 00:00 UTC on the cap.

## Risks

- No gap is open at placement: AVAX is 8 pct (USDT), 12 pct (DAI), 10 pct (ETH), 17 pct (WBTC), 30 pct (LINK, AAVE)
  above the old pools' levels. The bot may send nothing before the trials close.
- The pot is finite (old pools hold about 32,000 USDT, 6,500 DAI, 19 ETH) and `swapSupply` falls with every migration.
- A pool with a fee other than 0.3 pct makes the take revert in `eth_call` (logged `calc_gain_not_on_chain`), never sent.

## Fork proof

`python3 scratch/trial-aeb-migrate-avalanche/proof.py` (reset 100,875,859: USDT, flash from the Trader Joe pair,
`joeCall`) and `proof.py 100906874` (DAI, flash from the Pangolin pair, `pangolinCall`), about 1 min each: hashes and
deltas in the manifest and `proof-result-<block>.json`. `selftest.py` checks the paper code override through the relay.
