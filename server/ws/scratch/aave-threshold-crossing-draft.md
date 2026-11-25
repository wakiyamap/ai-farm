---
type: pitfall
chains: [arbitrum]
protocols: [aave_v3]
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
