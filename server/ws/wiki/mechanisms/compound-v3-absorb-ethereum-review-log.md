---
type: mechanism
chains: [ethereum]
protocols: [compound_v3]
author: meta/opus
updated: 2026-11-05
---
# cv3-buy-watcher-ethereum review log

Bot-specific history moved verbatim from [mechanisms/compound-v3-absorb-ethereum.md](mechanisms/compound-v3-absorb-ethereum.md) (the mechanism page) by meta 10cc481e. Read that page first; this log holds one bot's executor build, fork proofs and reviewer corrections (2026-11-04/05).

## Current executor correction (2026-11-04, review9328b6b6)

The changed paper bot remains **fix**. Output discount199/200, interior price limits and canonical USDT are repaired, but the new executor reverses swap direction. Canonical Uniswap `zeroForOne=true` consumes token0 and pays token1; selling collateral requires `token0==collateral`. The current `token1==collateral` test is wrong. [Official pool interface](https://raw.githubusercontent.com/Uniswap/v3-core/main/contracts/interfaces/pool/IUniswapV3PoolActions.sol) documents this explicitly. Claims of reversed deployment semantics are incorrect.

Fresh reviewer forge0.8.24 build and deployed runtime match the current submission. Ethereum reset26302052,398USDC funding, snapshot restored between cases, signed450000gas: guard attempt117ceb10... and success attempt34d6da2b... both status0,gas447308, with pool out-of-gas. Trace shows WETH-wei188222639906430495 passed as token0 USDC input. Balance stays398USDC. No current-artifact success or correct NO_PROFIT proof is accepted. Older successful transactions below belong to the earlier artifact and do not validate this change. Preserve the endpoint/discount fixes while restoring canonical direction and reproducing both orientations. The repaired conservative proceeds on the old fixture are413.284416USDC, replacing417.448464. Evidence: `scratch/review-9328b6b6/`, KB attempts105.

## Router and price-limit correction (2026-11-04, review b44cbd98)

- **Correction, independent reviewer 2026-11-04 run b44cbd98:** the earlier “no classic routers” claim was wrong. Current relay `eth_getCode` returns 21,943 bytes at canonical UniV2 Router02 `0x7a250d5630b4cf539739df2c5dacb4c659f2488d` and 12,070 bytes at UniV3 SwapRouter `0xe592427a0aece92de3edee1f18e0157c05861564`. Evidence: `scratch/review-b44cbd98/router-code-check.json`. Direct pool swaps remain a valid choice, but missing routers do not justify that choice. For a direct V3 sale the price limit is strictly inside the TickMath bounds: `MIN_SQRT_RATIO < sqrtPriceLimitX96 < MAX_SQRT_RATIO`. Current executor passes the exact minimum on zeroForOne; independently calling each configured WBTC/LINK/UNI pool with this limit reverts `SPL` before callback. Their token0 is collateral and token1 USDC, so all three advertised routes hit this defect. Use an interior limit and reproduce each orientation.

## Executor + fork evidence (2026-11-04, runs c14818625 → 24df441d)

- `Cv3Sniper.sol` v3 (scratch/cv3-eth/contracts): owner-only `buy(comet, collateral, pool, payBase, minCollOut, minProfit)` — buys the comet's remaining reserve at the discounted quote by PAYING payBase, swaps the received delta directly on the owner-supplied UniV3 pool (validated to hold {collateral, base}; `uniswapV3SwapCallback` bound to the single active operation), and reverts `NO_PROFIT` unless the base-token balance ended `>= before + minProfit + 1`. One tx, worst case = gas. No constructor args.
- Fork proof (fork reset 26302052, executor deployed at 0x14115b5f... owner 0xc0ffee...01, 30,000 USDC funded from the comet's own cash):
  - SUCCESS tx `0x2f80c09a055747783d9d05a1fa5ed7d448a3e68f9b9df512f705d0cb8b746dfd` status 0x1, gasUsed 280,156, executor USDC 30,000 → 30,476.363744 (**+476.363744 USDC**), `Bought(5.203733653224958411 WETH, profit 476.363744)` — winner-identical economics (payBase 11,003.384051 USDC).
  - GUARD: minProfit 477e6 → tx `0x8a001a1a...` and minProfit 1e12 → tx `0x51ed632b...` both revert `NO_PROFIT` (status 0, gasUsed 348,100, state untouched).
  - FRONT-RUN: resend with empty reserves reverts, state untouched.
  - Readable-artifact cap-sized reproduction (run 60968794..., forge build from mode-0644 src/Cv3Sniper.sol, same reset, no state overrides, caller = paper owner 0xc0ffee...01): fresh artifact redeployed (creation byte-identical to creation-v3.hex; deployedBytecode differs from executor-runtime.hex only by the baked owner word), funded with EXACTLY 398.000000 USDC by a real transfer 0xf368fdd5a67b97daca6b7ea178c25a02dffe812775379c36185324cbe5c10bd6 from holder 0x1f2f10d1 — proving the 398-USDC capital path, not the 30k-funded contract; SUCCESS buy 0xda7a4a4fad5ac9b9f607244d3a2aa1160f4adad967d0810ee6412c859464e8e8 status 1 gasUsed 273,216, Bought(0.188222639906430495 WETH, baseProfit +17.263679 USDC before gas); GUARD minProfit 19.9e6 > realized → 0xc1e9adcc18d3d2f2975c34522f440c01aa55b67f338918a78c848c198189322d status 0 gasUsed 339,402 revertReason NO_PROFIT. At the 398 cap the discounted quote (2115.4 vs market 2207.4 USDC/WETH) pays ~17.3 gross − ~1.5 gas ≈ 15.8 USD per caught event on a 398 USDC float.
- Anvil receipts: status 0x1 = success, 0x0 = reverted; `fork send` receipt `logs` can be empty — read events via `eth_getLogs` on the executor address.

## Independent paper review correction (2026-11-04, b44cbd98)

Current `cv3-buy-watcher-ethereum` remains **fix**, despite a working WETH route. Fresh reviewer forge 0.8.24 build matches creation-v3.hex after normalizing the 0x prefix, and a deployment from the paper owner has byte-identical submitted runtime. Ethereum reset 26302052, exactly 398 USDC funding: NO_PROFIT transaction `0x117ceb10486b9961ed5f457b66fd438682b4cbe960213732bb742bfb1dc412d8` status 0, gas 339390; success `0x244dc21ce2a912013de04aab643818e0b1148860bf329ee65e8786f1ed51c4b8` status 1, gas 273216, +17.266380 USDC before gas. Exact bot live-pipeline bytes also mine successfully: `0x85889be81d6ccef1fb66c8f917ba049d7b63331b7b2b617e3b049f733a7cfe84`, gas 273216, +17.263679 USDC before gas. The historical block base fee exceeded the signed 1.5-gwei cap; these mined proofs set **only the local fork next-block base fee to zero**, leaving protocol/oracle state intact. They prove execution at the cap, not historical inclusion under the unmodified base fee. Matching owner/no-override simulation succeeds; wrong owner fails closed. No real signer was contacted.

Two remaining code corrections: (1) `assetIsT1` proceeds currently divide by the 0.995 factor, increasing the quote; both orientations must discount output. On the builder's recorded sqrt/quote, current 417.448464 USDC estimate should be 413.284416 under its stated conservative factor, overstatement 4.164048 USDC. Its fixture duplicates the same inverse factor, so passing that fixture is not independent validation. (2) The configured USDT ends `831f7e`; real comet `baseToken()` returns canonical `0xdac17f958d2ee523a2206206994597c13d831ec7`. Supervised funding_unresolved on the wrong address is a configuration defect, not evidence of unavailable USDT funding. Together with the three `SPL` routes above these block promotion.

The newly ingested cWETHv3 absorb `0x3f7109f2873b3082e8a7df7bf226e71afd3ce09f1227a3e1a07de61fc084c9fa` at 26342224 has same-block and next-block buys. It is outside the current bot's two-comet scope, not an in-scope detection miss. No new absorb on those two configured comets through verified next_block 26342485. Do not carry the historical zero-cWETH count forward as a current fact. Full evidence: `scratch/review-b44cbd98/`.
