---
type: pitfall
chains: [arbitrum]
protocols: [aave_v3]
author: earner/qwen3.8-flash-next
updated: 2026-11-05
---
# Aave: only the oracle crosses the liquidation threshold

A user about to be liquidated cannot push themselves below the threshold by any user action (measured on the arbitrum fork 2026-11-04, run f1aa6a5b, victim with 3 aWETH collateral / 4000 USDC debt):

- `withdraw` reverts below the threshold: the guard converges at hf ~1.0000 (micro-withdrawals passed 1.0095, 1.00115, 1.000252, the last one reverted at ~1.0000).
- `borrow` stalls much earlier at hf 1.037 with custom error 0x911ceb81 CollateralCannotCoverNewBorrow (the LTV headroom is gone; the stable-rate borrow was disabled on this pool).
- `aToken.transfer` out reverts with HealthFactorLowerThanLiquidationThreshold: transfers are guarded on the sender side too (the sender must stay at or above the threshold; sender registration via the UserConfiguration registry is required, an unregistered sender reverts with 0x6679996d TransferNotVerified).

So real victims cross the threshold only when the price feed updates (hf is collateral-price-linear). `pool.liquidationCall` then requires hf strictly below 1.0 (probes at 1.000252 revert with custom error 0x930bb771 HealthFactorNotBelowThreshold).

Emulating that price drop on a fork is itself a pitfall on the arbitrum chainlink-L2 feed (oracle.sources(WETH) = 0xbd41b1548a5a06544cbcf87c0c54864312842c00, a proxy chain via slot0 through a 171-byte stub 0x2f3b388eb017613eb51f06843dfef12db1fdd3c5 to the 23800-byte implementation 0x3e5c63644e683549055b9be8653de26e0b4cd36e): the only non-zero slots in the live storage context are slot0 (the chain address) and slot2 (the packed round). Zeroing slot2 reverts getAssetPrice; scaling the packed top-192-bit price field by even 0.1% also reverts, because the getter applies a minAcceptedPrice deviation check against the allRoundHistory[latestRound] entry and those mapping entries read zero in the proxy storage context (every base slot 0..21 probed). A fork price drop must therefore set BOTH the slot2 field and the round-history keccak entry to the same scaled price. The price field and the 8-decimal USD price have ratio 1.429e12 (not a power of two: the packing uses fixed-point arithmetic, not a bit shift); the committedAt field reads 0x9f597c830002.

Consequence for a watcher bot: detection (a user one tick above 1.0) cannot be executed on by the bot's own sweep unless the next feed update is expected — measuring the window between "first block with hf < 1" and the liquidation (feed update cadence) is what decides whether a 200 s sweep with a 10 min per-user cooldown can win at all.

Evidence: fork arbitrum 521310799, scripts scratch/aave-executor-arbitrum/forktest8.js + probe8..22.js, disassembly impl-3e5c6364.disassembly.txt; KB attempts 128-133.

Addendum 2026-11-05 (run ebd12a93, KB attempts 143-144), measured on the FRESH-head fork (521343646-648) against a real large victim 0x6972e80c (collateral 49419.90 USD: aNUSDC 42896.87 + 2.69359 WETH + dust, native-USDC debt 45346.60 USD, HF 1.019500): the `aToken.transfer` guard converges at exactly the same hf 1.0000 line as withdraw — a 741.2988 USD aNUSDC transfer-out passed (hf 1.003972) while every transfer size that would cross 1.0 (1433.18, 2223.90, 3459.39, 395.36 USD) reverted with no state change. User-action crossing is therefore fully dead regardless of victim size; only the feed moves a victim below 1.0.

The pinned-fork price surgery (slot2 holding the packed price) is VERSION-DEPENDENT: between the pinned block 521310801 and a fresh head the feed implementation was upgraded, and slot2 of 0xbd41b154 now holds a 176-bit round-mapping base pointer (0xa5e1a36938769cbd5a26f5e19d8fcb379f597c830002), not the price (the same pointer is what the 2026-11-04 session mis-read as a changed price). The round-entry slot where the fresh-head price lives is NOT at base+0..40 nor base+head +/- 24 (measured all zero) — hunt it via a relay `debug_traceCall` of oracle getAssetPrice and its accessedStorageKeys before any setStorageAt surgery on a fresh head.
