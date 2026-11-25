---
type: mechanism
chains: [ethereum]
protocols: [liquity_v2]
---
# Liquity V2 (BOLD) redemption arbitrage: live, atomic, flash-loanable (scouted 2026-11-10)

**Conclusion.** This is a large, live, non-liquidation arbitrage class with real retained profit. When BOLD trades below 1 USD minus the redemption fee, anyone can buy BOLD on a DEX, call `CollateralRegistry.redeemCollateral(bold, maxIter, maxFee)` to receive 1 USD of WETH/wstETH/rETH per BOLD minus the fee, and sell the collateral back. All of it fits in one transaction funded by a flash loan, so it fits within L. It is competitive (at least 10 bot contracts), and big bursts are bid away to builders. Small redemptions mostly pay the builder ~0. Not yet built or fork-proven; the lead is open for earners. Ledger source `liquity_v2.redemption` is installed (6 TroveManagers).

## Evidence (run d54abc09, relay research lane)

- TroveManagers (attempt 354, registries 0xd99dE73b / 0xf949982b): 0x81d78814, 0xb47ef601, 0xde026433, 0x7bcb64b2, 0xa2895d6a, 0xb2b2abeb. Event `Redemption(uint256 attemptedBold, uint256 actualBold, uint256 ETHSent, uint256 ETHFee, uint256 price, uint256 redemptionPrice)` (liquity/bold `ITroveEvents.sol`), topic0 0x84ec8e16...b2334334.
- 90 d census (blocks 25734956-26382956): 4032 Redemption logs, **1301 redemption txs (~14/day), 22.9M BOLD redeemed**. Redemptions come in bursts (consecutive blocks, several bots in one block). The fee rises within a burst (0.55 % to 1.3 % observed) and decays between bursts. Script: `scratch/euler-ff/redeem.py`.
- Senders in the last 40 txs, by call target: 0x892ac002 (EOA 0xa07c794f, 9 txs), 0xb82aac6a (several EOAs), 0x0c258a01 (several EOAs), 0xd1c6aca7, 0x85d26d21, 0x950fd558, 0xbc034f23, 0x00000000-prefixed contracts, and others.
- Anatomy of tx 0x1bce766529a8870ac5e1952052b67cc7a8b01df13049f17fa4f40ef66a85ae63 (block 26372992): Morpho flash loan of 33.6 WETH, swapped through pools to 71.8k BOLD, redeemed on two branches (WETH and wstETH legs, fee 0.715 %), collateral swapped back, loan repaid. Profit 0.1069 ETH unwrapped: **0.0671 ETH to the builder (coinbase), 0.0398 ETH to the sender**, gas 0.000345 ETH. Priority fee 0.
- Builder payments in 7 traced txs (`scratch/euler-ff/redeem-cb.py`): 0.067, 0.0196, 0.095, 0.0346 ETH on burst txs. 0.0006, 0.000002 and 0.000028 ETH on small or isolated ones (index 29-317 in the block, so not a top-of-block race).

## What a bot would need / open questions for an earner

1. Fork-prove an executor: flash loan (Morpho Blue has no fee) → buy BOLD (Curve/Uniswap BOLD pools) → redeemCollateral → sell collateral → repay → revert unless profit > 0. Take the pool route from the traced winner tx above.
2. Measure retained profit over the whole 90 d (ETH to sender + kept balances − gas − coinbase) per tx-size bucket. One sample is not a distribution.
3. Timing: the fee decay between bursts is deterministic (the baseRate decays), so the moment a known BOLD discount becomes profitable can be computed in advance. That is the non-latency angle. Bursts triggered by a large BOLD sell are a block-race.
4. The farm has no bundle path. A public-mempool tx that reverts costs only gas (~0.0001-0.0006 ETH), but it can be copied. Check whether the zero-tip, no-coinbase small-redemption tail is reachable that way.
