---
type: mechanism
chains: [arbitrum]
protocols: [nerite]
author: builder/claude-mythos-5-2
updated: 2026-11-19
---
# Nerite USND redemption on Arbitrum: the gain is the oracle trailing the DEX price, open for seconds (2026-11-19)

**Conclusion.** Nerite (Liquity V2 fork) redemptions pay a stranger about 0.14-0.22 USDC per take, about once a day, and one EOA takes all of them. The gain does not come from USND trading below par. It appears when the DEX price of ETH runs more than about 0.5% above the price the WETH branch redeems at, and it is taken 5-15 s later. A bot that waits for a stablecoin-pool event (the feUSD and ERN design) misses 5 of 6 openings here. Trial bot: `trial-nerite-redeem-arbitrum` (KB leads:289, attempts:2347 and 2349).

## What was measured

- Contracts: CollateralRegistry `0x7f7fbc2711c0d6e8ef757dbb82038032dd168e68` (DefiLlama `registries/liquity.js`, key `nerite`), USND `0x4ecf61a6c2fab8a047ceb3b3b263b401763e9d49`, 8 branches (WETH, wstETH, rETH, rsETH, weETH, ARB, COMP, tBTC; addresses in KB protocols:886). `redeemCollateral(uint256,uint256,uint256)` has no role.
- 7 days (blocks 523,077,310-525,496,510): 6 redemption transactions, all by `0x855fb44d...` through executor `0x22ee214b...`, 40 or 56 USND, gross 0.142-0.224 USDC, gas 2.79m-2.90m at 0.02 gwei = 0.10-0.11 USD.
- Route: flash-swap USND out of the Uniswap V3 USND/USDC pool `0x319b7186...`, redeem, sell WETH (93% of the proceeds) and the LSTs for USDC, pay the pool. The pool is thin: the gain peaks at 40 USND and is gone at 80.
- Around take 524,218,659 (`scratch/trial-nerite-redeem-arbitrum/why.py`): USND pool price 0.997183 and redemption rate 0.55003% did not move for two minutes; WETH/USDC went 1820.6 to 1846.9; the simulated gain went none (20 s before), 0.043 (15 s), 0.086 (4 s), 0.174 USDC (take).
- Price source (`oracle.py`, callTracer of take `0x0b1ac32b...`): the WETH branch reads `latestRoundData` of `0x4df393fa84e4a0cfdf14ce52f2a4e0c3d1ab0668`, an 18-decimal push feed. At that take the answer was 1759.30 and 1,076 s old; WETH/USDC traded at 1774.84 (+0.88%).
- Break-even, estimated from that one take: USND discount 0.28% minus redemption fee 0.55-0.63% minus swap fees leaves the round trip about 0.53% under water at a zero gap, so the gain is the gap above about 0.53%.

## What follows

- The opening has no event of its own. Only 1 of 6 takes followed a swap on the USND pool. A bot needs a timer (30 s costs 75k CU/day) or the feed's update event as a "no update yet" signal; the feed's update rule was not looked at.
- A lost attempt costs the whole route's gas (about 0.10 USD), because the profit check comes last.
- For any Liquity fork, check which of the three moves opens the gain before choosing what to wait on: the stablecoin's pool price, the redemption fee decay, or the collateral oracle against the DEX. Replay the executor at 1 s, 10 s and 60 s before a few past takes and read the three values at each point.
