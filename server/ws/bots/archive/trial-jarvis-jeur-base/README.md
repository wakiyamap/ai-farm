trial: Jarvis jEUR / EURC fixed-rate wrapper round trips on Base. Measures by sending how often the farm, looking when the jEUR/USDC pool emits a Swap (farm feed) and on a 5 min safety poll, finds a gap between the jEUR/USDC pool and the EURC/USDC pool that the one incumbent has not taken.

## Mechanism

jEUR (Jarvis Synthetic Euro, 0x4154550f4db74dc38d1fe98e1f3f28ed6dad627d, 18 decimals) is minted from EURC and burnt back to EURC 1:1 by anyone through `SynthereumFixedRateLendingWrapper` 0x41b0667ea45a5401d95f9a5d281287630704b798 (Blockscout-verified; `wrap(uint256,address)` and `unwrap(uint256,address)` carry only `nonReentrant`; `conversionRate()` = 1e18; 1.11M EURC of collateral sits in a Morpho vault). jEUR trades against USDC in pool 0x9a8f6327dd5a9fc87ee9be06cf7fd2e069efb62b (fee 0.0486 pct, 75k jEUR + 83k USDC) and EURC against USDC in pool 0x6eaec4f69c92bd16a4b018ceb6fe7a446a113598 (fee 0.007 pct). Both are UniV3-style pools of factory 0x9cb22058 (`swap` 0x128acb08, `uniswapV3SwapCallback`). EUR/USD moves all day, the EURC pool follows it, the thinner jEUR pool lags, and a round trip pays, in one transaction through the executor:

1. Flash-borrow 300-5,000 USDC from Morpho Blue 0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb (`flashLoan`, fee 0).
2. `unwrap` route: USDC -> jEUR (pool 0x9a8f), `unwrap` (rounded down to a multiple of 1e12 wei), EURC -> USDC (pool 0x6eae). `wrap` route: USDC -> EURC, `wrap`, jEUR -> USDC.
3. Repay; revert `NoProfit` unless the USDC balance grew by `minProfit`; pay the whole USDC gain to the bot wallet; send the sub-1e12 jEUR dust to the owner so the executor holds nothing.

Copied from executor 0x1470dab4a3fb2951d1c2e3525628c0ca65352ac9 (only caller: EOA 0x62e88a85c3b9ca889448744234665c6e0e706f73), take 0xd3024e21d9ab15a7f20fabdef46de95c975189afe13e3aa13703c3f57a9fa526: 2,714.83 USDC -> 2,467.757571 jEUR -> 2,467.757571 EURC -> 2,714.98 USDC, kept 0.144132 USDC for 993,388 gas at 0.00735 gwei (0.013 USD). Found by the flash-recipient census of run cb0420ed (attempts:2542, lead 301).

## Competition, last 7 days (blocks 56,522,824-59,546,824, `scratch/flash2-cb04/jarvis7d.py`, `jarvis7d.json`)

552 Wrap / Unwrap events at the wrapper. Arbitrage executors: 0x1470dab4 (119 events since block 58,437,845 = about 47 a day; its earlier executor 0x20c22ae5, 31 events) and 0xd9afda02 (195 events, silent since block 58,849,735, 3.8 days). The rest are aggregator routes (0x8f10b468 159, 0x11111605 15) and users. So one active operator. Its sampled takes kept 0.010, 0.036, 0.055 and 0.144 USDC; tx index 2-88; priority fee 0.002-0.03 gwei; 8 of its 25 newest listed sends failed.

Blocks to take (24 newest takes of 0x1470dab4; the farm executor's `probe()` as a code override at blocks before each take, `scratch/trial-jarvis-jeur-base/series.py`, `series-windows.json`; 0.2 s blocks):

| a gain was already visible | at the parent block | 1 block earlier | 2 | 5 (1 s) | 15 (3 s) | 50 (10 s) | 150 (30 s) | 450 (90 s) |
|---|---|---|---|---|---|---|---|---|
| takes of 24, any gain | 24 | 24 | 24 | 20 | 17 | 13 | 13 | 9 |
| takes of 24, gain of 0.019 USDC or more (about what one send costs to sign) | 19 | 18 | 17 | 9 | 7 | 3 | 2 | 1 |
| takes of 24, gain of 0.023 USDC or more | 18 | 17 | 15 | 6 | 4 | 0 | 0 | 0 |

Reading: the incumbent sends once the gain passes about 0.03 USDC and then lands within 1-3 blocks (0.2-0.6 s) of the jump; the farm cannot win those. Below that line small gains stand for a long time: 0.0229 USDC for 90 s before take 59,446,210, 0.0226 USDC for 30 s before 59,474,246, 0.0226 for 10 s before 59,524,956. Those are what this trial sends at: 3 of 24 takes had a gain above the bot's own line (about 0.021 USDC: the signed cap at the minimum tip, plus 10 pct) standing 10 s or more, so roughly 6 chances a day at 47 takes a day, each worth about 0.023 USDC gross against about 0.010 USD of real gas (1.1m gas at 0.005 gwei). The margin is thin: nothing at 0.023 USDC or more stood 10 s. This is a win-rate measurement worth cents a day, not revenue. `selftest.py 59446159` (51 blocks before take 59,446,210): `paper_sim` success, gross 0.022957 USDC, cap 0.0207 USD.

## How it sends

`check()` runs when the farm feed delivers a `Swap` log of the jEUR/USDC pool (`/logs/base`, address `0x9a8f6327dd5a9fc87ee9be06cf7fd2e069efb62b`, topic0 `0xc42079f9...bcca67`; 113 logs a day), on a feed `gap`, removed log, 429 / 503 or connection error (state re-read, then no feed call for 60 s), on a 300 s safety poll, and 10 s and 40 s after a look that left a gain standing below the send line (a follow-up arms nothing). The EURC/USDC pool Swap (about 4,100 a day) is a busy event and is not subscribed. Measured 2026-11-20 over 24 h (`scratch/trial-jarvis-jeur-base/feedtrigger.json`): a gain of 0.019 USDC or more was visible 1.2 s after 3 of the 113 events, 10 s after 4, 40 s after 5. Each look:

1. One `eth_call` of the executor's `probe()`: both directions at 300 / 700 / 1,200 / 2,000 / 3,000 / 5,000 USDC, every trial reverted inside the call, gains returned. All zero = nothing to take.
2. Read budget: a best gain under 0.015 USDC (below any signed cap) stops here with a `check` row `gain_below_gas`; a gain just found below the cap is not re-examined for 5 minutes unless it grew by 3 pct (`gain_unchanged_below_cap`). Otherwise, for the best (direction, size): latest base fee, ETH/USD from `slot0` of the Uniswap V3 WETH/USDC pool 0xb4cb8009 (the gain is USDC, the gas is ETH), `eth_estimateGas`.
3. Gas limit = estimate x 1.20 + 200,000 (refused above 2.5m). Tip = min(0.05 gwei, 20 pct of gross / gas limit, what the gross can afford), at least 0.0001 gwei. `maxFeePerGas` = base fee x 1.05 + tip (refused above 0.1 gwei).
4. cap = gas limit x maxFeePerGas + 1e11 wei L1 allowance, converted to USDC units at the pool price. Send only if the simulated gain is at least cap x 1.10 + 1, with `minProfit` set to that, after simulating the exact call at the signed gas limit. Typical cap 1.1e13-2.6e13 wei (0.02-0.05 USD).
5. Live: the wallet bound below, then one signer call. One send per look, 20 s cooldown per direction.

A lost attempt costs gas only: about 1.2m gas x 0.005 gwei = 6e12 wei, 0.011 USD.

## The 1 USD per-send bound

Base charges the L1 data fee and the operator fee at inclusion; no signed field bounds them. The enforceable worst case of one send is the wallet's native balance, so the wallet stays under 1 USD: `capital_usd: 0.75`, all native, no top-up, and right before the signer call `take()` reads the wallet balance and ETH/USD and refuses the send while balance x price is 0.95 USD or more (`opportunity_skip`, `wallet_at_or_above_usd_bound`). Profit arrives as USDC, so wins do not raise the native balance. A balance below the cap logs `wallet_below_gas_cap`: the trial is over. 0.75 USD is the deployment (about 0.01 USD) plus about 60 lost attempts.

## Fork proof

`python3 scratch/trial-jarvis-jeur-base/proof.py [parent block] [result file]` (leases and releases the Base fork; reset, deploy, fund, probe, non-owner, guard, success, repeat, leftovers). Results are in the manifest's `fork_evidence`. `selftest.py <block>` checks the bot's hand ABI encodings against `cast calldata` and replays the bot's own `check()` at a past block.

Note for a re-run on 2026-11-19: the fork lane is over its daily budget and the public node sometimes refuses archive reads (HTTP 403 in `fork deploy`); a retry a minute later passed both times.

## Reads

About 22,000 CU/day, 0.012 USD at 0.53 USD per million CU. Relay: safety poll at most 288 x 26 = 7,488 CU, feed looks 113 x 26 = 2,938, follow-ups about 1,560, an opportunity about 150 (block, slot0, estimate, guarded call; live also balance and receipt polls); the code stops at 60,000 relay CU/day. Feed: 113 logs x 924 bytes x 0.04 = 4,180 CU plus about 4 CU a minute for the idle subscription, about 10,000. No per-block polling.

## Logs and closing

`logs/bot.jsonl`: `start`, `check`, `opportunity` (probe table, estimate, limit, tip, cap), `opportunity_skip`, `simulate_revert`, `paper_sim`, `wallet_bound`, `send`, `send_result` (won / lost, gas used, L1 fee, the winner's block and tx = the last Wrap / Unwrap at the wrapper up to our block), `signer_reject`, `read_budget`, `loop_error`. After 7 days live or when the gas is spent: count sends, wins and net USD, write an `attempts` row and set lead 301 `measured` (win rate, net/day) or `blocked_infra` (how many blocks late, how much fee short).
