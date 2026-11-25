# trial: trial-cv3-buy-arbitrum

**Trial bot** (decision 2026-11-17-cheap-chain-trials): cheap chain, race rule and EV floor
waived, the win rate is measured live by sending. Arbitrum copy of the live
`trial-cv3-buy-base`, with a new executor that also covers the USDT comet.

After anyone absorbs an underwater account on Compound v3 Arbitrum (cUSDCv3
0x9c4ec768c28520b50860ea7a15bd7213a9ff58bf, cUSDTv3 0xd98be00b5d27fc98112bde293e487f8d4ca57d07),
the collateral sits in the comet's reserves and anyone may `buyCollateral()` it at the comet's
discount (both comets are below `targetReserves`, so the sale is on). The executor
`Cv3FlashBuyOut` does it with no principal, in one transaction: flash-swap on a UniV3
{collateral, base} pool (sell exactly the quoted collateral), pay the comet from the pool's
base token inside the callback, sell a USDT surplus to USDC on the UniV3 USDC/USDT 0.01 % pool,
revert unless the USDC surplus exceeds `minProfit`, send the USDC to the bot wallet.

## Competition, last 7 days (ledger compound_v3 arbitrum, blocks 524,048,877-524,328,185)

- 8 AbsorbCollateral events in 6 txs by 2 absorbers (0xd12810b1 through Atlas, 0xf399972c);
  10 BuyCollateral by 4 buyers. 6 buys are in the same transaction as the absorb.
- 4 residue buys (no absorb in their own tx), 2 executors, receipts in
  `scratch/trial-cv3-buy-arbitrum/receipts.json`:

| buy tx | block | blocks after absorb | executor | paid | gross | gas used | priority fee | gas cost |
|---|---|---|---|---|---|---|---|---|
| 0x8dd4d06d..06ec | 524,328,185 | 1 (0.25 s) | 0x44d8fa1e | 49.34 USDT (WETH) | 2.06 USDT | 358,237 | 1.525 gwei | 0.000554 ETH (~1.0 USD) |
| 0x2e7b1c22..f91d | 524,048,878 | 1 (0.25 s) | 0x44d8fa1e | 148.89 USDT (wstETH) | 9.44 USDT | 609,085 | 1.868 gwei | 0.00115 ETH (~2.1 USD) |
| 0x7c2b4442..fced | 524,319,773 | 2 (0.5 s) | 0x48daab9f | 2.71 USDC (WETH) | ~0.12 USDC | 498,419 | 0 | 0.000015 ETH (~0.03 USD) |
| 0x4df994fe..70ad | 524,174,704 | n/a (dust) | 0x48daab9f | 0.03 USDC (WETH) | dust | 446,512 | 0 | 0.000013 ETH |

- The residue is taken 1-2 blocks after the absorb, far inside the farm's reaction time. This
  bot wakes on the feed (~1 s after the block) and expects to lose unless the incumbents are
  late or absent; it bids at most 25 % of gross under a 0.2 gwei fee cap (the incumbent
  0x44d8fa1e pays 1.5-1.9 gwei, about half of its gross).

## Fork proof (`scratch/trial-cv3-buy-arbitrum/proof.py`, arbitrum fork gen 23-24, output `proof.out`)

One script: lease, reset, deploy with constructor arg = owner, checks, release.

Case A, reset 524,328,184 (parent of the first table row), cUSDTv3, WETH via UniV3 WETH/USDT
0.05 % 0x641c00a8..c79d, payout through USDC/USDT 0.01 % 0xbe3ad6a5..eef6:

- DEPLOY 0x0ca84d7a15153049ad8513da838123004462b379ab66cf8d93566fe09a0ddf90 gas 950,161
- NON-OWNER 0xb2b600b441d7a7afccb9662b86e829a20b083c5e485d3a4a4429d15be260499a status 0
- GUARD (minProfit 1e12) 0x35480cf9f351a2a8dec87276373be6b02e9636b6ae4eb8608de9328e2f9154fe
  status 0, NoProfit, gas 485,617, owner USDC delta 0
- SUCCESS 0x2e064b155b05e9274a9668a090f7cedfaa7044c2aa11a721551cecdd111069c0 status 1,
  gas 412,231, block 524,328,188: paid 49.116682 USDT for the WETH residue, **owner wallet
  +2.107212 USDC** (= the eth_call simulation). Executor afterwards: 0 USDC, 0 USDT, 0 WETH,
  0 native, allowance to the comet 0.
- NOTHING-LEFT (same call again) 0x820132b329fafd97745d17f85830e5e2b92077c32f37fa8da2333b5da9f5090b
  status 0, owner USDC delta 0.

Case B, reset 524,319,772 (parent of the third row), cUSDCv3, WETH via UniV3 WETH/USDC 0.05 %
0xc6962004..e8d0, no out pool:

- SUCCESS 0x1d99e1b112213a3b9f3d2b910c6c3c7dda2249583426241ebf8958e75d09371f gas 331,946,
  **owner wallet +0.118458 USDC**; NOTHING-LEFT 0xf551a880bce6e974ba204e5675b21e094b00e3eefe2ec32e3fa9f699c86b1677 status 0.

`scratch/trial-cv3-buy-arbitrum/paper_selftest.py` runs this bot's own `check()` on the fork at
524,328,184: Multicall scan finds 49.36 USD of WETH in cUSDTv3, simulated gross 2.107212 USDC,
gas limit 641,818 (estimate x 1.25), gas cap 0.51 USD, `paper_sim` success (`selftest.out`).

Paper mode simulates the exact call with `eth_call` and a code override (the fork runtime,
`executor-runtime.hex`) at the fork address 0xfe00ddfe..8e9a, from the owner baked into that
runtime (0xc0ffee..02). Live mode uses the signer's address and `EXECUTOR_ADDR`.

## What the bot waits for

- Feed `/logs/arbitrum`, address = the two comets, topic0 = AbsorbCollateral
  `0x9850ab1af75177e4a9201c65a2cf7976d5d28e40ef63494b44366f86b2f9412e` (8 events / 7 d, bursty).
- On `gap`, `removed`, HTTP 429 / 503 / 400 or a connection error: re-read the reserves
  through the relay (at most once a minute while the feed is down), then continue.
- Safety poll of the reserves every 10 min (one Multicall3 `eth_call` for all routes).
- Routed collaterals per comet: WETH, WBTC, wstETH, ARB, GMX, each with one or two direct UniV3
  {collateral, base} pools (factory 0x1f98431c..f984 `getPool`, listed in `bot.py` MARKETS);
  the best simulated pool is used. ezETH, wUSDM, tETH, tBTC are not tried.

## Send rule and loss bound

Send only when the simulated USDC surplus is above that send's gas cap:
`gasLimit x maxFeePerGas x 4,000 USD/ETH`, with `gasLimit = eth_estimateGas x 1.25` (refused
above 1,200,000), `maxFeePerGas = min(0.2 gwei, 2 x base fee + priority)` and priority = at
most 25 % of gross. The cap is below 0.96 USD by construction; `minProfit` in the call is that
cap, so a mined transaction either nets more than its gas cap or reverts (`Cv3FlashBuyOut.sol`
NoProfit check). Worst case per send = gas. Every send logs `send_result` with won / lost, gas
used, gas cost, the winner's block and how many blocks after it we landed.

## Reads

Safety poll: 144 Multicall `eth_call`/day x 26 CU = 3.7k CU. Absorb wakes: ~1/day x (1 scan +
up to 4 sims + estimate + gasPrice) = under 0.5k CU. Feed: ~4 CU/min subscription = 5.8k CU
plus ~35 CU per event. Total ~10k CU/day = 0.005 USD/day at 0.53 USD per 1M CU; the bot stops
reading at 60k relay CU/day (`CU_CAP`).
