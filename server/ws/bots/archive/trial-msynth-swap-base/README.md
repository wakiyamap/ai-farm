trial: Metronome Synth synth-to-synth swap at oracle price versus the Aerodrome msUSD / msETH pools on Base.

## What it does

Metronome Synth's Pool (0xc614136d6c5ab85bc2acf0ec2652351642d7f54e) lets anyone swap msUSD for msETH at the
protocol's oracle price (`swap(synthIn, synthOut, amountIn)`, selector 0xdf791e50; the swap fee is 10 pct of the
output at the moment). Both synths trade far under their pegs (msUSD about 0.80 USDC, msETH about 0.87 WETH on
2026-11-23), so the pools' msETH / msUSD ratio is free to drift. When it is more than the fee above the oracle rate:

    Morpho flash loan USDC -> msUSD (Aerodrome pool) -> Pool.swap -> msETH -> WETH (Aerodrome pool) -> USDC (Uniswap V3)

One transaction through the SynthLoop executor; it reverts unless the USDC balance grew by minProfit (= the send's
gas cap), and sends all USDC to the bot wallet. No principal, no holding.

Timer bot: every 60 s two eth_calls (the exact `run()` on two pool sets at 400 USDC); a revert means no gap. On a
gain above 0.03 USDC: the two mixed pool sets, sizes 800 / 1,200 / 1,600 / 2,400 USDC, gas estimate, send. After a
live send it looks again in 10 s (the gap usually stays open for many takes).

## Last 7 days of competition (to block 61,039,601; scratch/ra0c6/profits.json)

42 swap transactions at the Pool, 4 contracts:

| contract | takes | profit per take | gas | priority fee | tx index |
|---|---|---|---|---|---|
| 0x117a6196964d096194b4991bf7040a84c2fee552 (EOA 0x61c658e4) | 27 | 0.0000138-0.00102 WETH (sum about 0.0062 WETH) | 4.2-4.5M gas, 0.00003-0.00013 ETH | 0.0006-0.005 gwei | 12-156 |
| 0x281f65f56f57c0b94011d3ff6610ded4651a8714 | 11 | not sized (leaves in another form) | 0.9-1.05M gas | 0.018-0.021 gwei | 2-68 |
| 0x2a79a56320e68e584cfa33c4045a887923aee680 | 1 | 0.00056 WETH | 1.09M gas | 0.001 gwei | 121 |
| 0xb263c370d8c309f61ce0c9c954f39fd2d6e0c7e5 | 3 | 0.00004-0.00017 WETH (dust sizes) | 1.3M gas | 0.007-0.027 gwei | 4-31 |

Timing: 38 of the 42 are one burst, 2026-11-20 15:48:21-16:36:57Z (blocks 59,996,628-60,011,209, 2,916 s); takes
0-1,421 s apart (median 14 s). Blocks to take: the gap was already open 50 blocks (10 s) before the first
incumbent take (this bot's eth_call pays 0.91-1.20 USDC per 400 USDC there) and it was never closed by the takes:
2.13-2.38 USDC per 400 USDC 332 s in, 0.58-2.41 USDC at the end of the burst (scratch/trial-msynth-swap-base/
selftest-result.json). A smaller gap (0.26-0.31 USDC) 300 s before the burst was taken by nobody. No fee bidding to
speak of: priority fees 0.0006-0.03 gwei, base fee about 0.005-0.02 gwei.

## Limits

- capital 5 USD (gas only), at most 0.95 USD a send (2.4M gas x 0.15 gwei + L1 fee at a 2,500 USD/ETH reference);
  typical attempt 0.01-0.05 USD.
- sends only when the simulated gross > 1.3 x the send's gas cap; minProfit = that cap.
- priority fee at most 1/10 of the gross, never above 0.1 gwei.

## Read cost

2 eth_calls a look x 1,440 looks a day x 26 CU = 74,880 CU/day, plus about 200 CU per hit; cap 95,000 CU/day in
code (then it sleeps to 00:00 UTC). About 76,000 CU/day = 0.04 USD at 1M CU = 0.53 USD. No feed filter.

## Files

- `bot.py`: the bot; `executor-runtime.hex`: paper code override (eth_getCode of the fork deployment).
- executor source: `scratch/trial-msynth-swap-base/contracts/src/SynthLoop.sol`
- proof: `scratch/trial-msynth-swap-base/proof.py` (result `proof-result.json`), `selftest.py`.

## Notes

- The Pool's quote depends on block time (on the fork the same call paid 2.83 USDC in one block and 4.53 USDC one
  second later), so a send can pay more or less than the look; the NoProfit guard decides.
- Live needs `EXECUTOR_ADDR_BASE` or `EXECUTOR_ADDR`; the `start` log line names the executor.
