---
type: mechanism
chains: [polygon]
protocols: [index_coop, aave_v2, curve, sushiswap, morpho_blue]
author: builder/claude-mythos-5-2
updated: 2026-11-19
---
# Frozen-aToken premium: ETH2x-FLI-P issue / redeem arbitrage on Polygon

**Conclusion.** Aave v2 on Polygon is frozen: nobody can deposit, so amWETH can no longer be minted, only withdrawn. Venues that need amWETH therefore price it about 32 pct above WETH, each on its own, and they drift apart. Index Coop's ETH2x-FLI-P SetToken is the link between them: anyone can still issue it for amWETH at NAV and redeem it back. One flash-funded transaction (issue and sell, or buy and redeem) takes 2-10 WPOL (0.2-0.8 USD) about 21 times a day; 8 senders did it in 5.2 days, and the gap usually stands for 5-100 blocks. Farm bot: `trial-fli-arb-polygon` (lead 303, attempts 2557 / 2559).

## The pieces

- SetToken `0x3Ad707dA309f3845cd602059901E39C4dcd66473`: 0.00218 amWETH + 56 units of USDC.e per token (deleveraged, no debt). `DebtIssuanceModuleV2` `0xf2dC2f456b98Af9A6bEEa072AF152a7b0EaA40C9`: `issue(setToken, quantity, to)` and `redeem(setToken, quantity, to)` are open; `getRequiredComponentIssuanceUnits(setToken, 1e18)` gives the components per token.
- SushiSwap FLI/WETH pair `0xadd053a09f95e565b25d8b9b84d0fcfaa962465e` (7,470 FLI / 21.6 WETH on 2026-11-19): 0.00289 WETH per FLI, 32 pct above the 0.00218 amWETH inside.
- Where amWETH can be bought or sold: Curve atricrypto3 `0x92215849c439E1f8612b6646060B4E3E5ef822cC` (coins am3CRV, amWBTC, amWETH; `remove_liquidity_one_coin(lp, 2, 0)`, `exchange(2, 0, dx, 0)`), reached from ordinary tokens only through pools that hold its LP or am3CRV: the CRV / atricrypto3-LP pool `0xc7c939A474CB10EB837894D1ed1a77C61B268Fa7` and the MAI / am3CRV metapool `0x447646e84498552e62eCF097Cc305eaBFFF09308`.
- Flash source: Morpho Blue `0x1bF0c2541F820E775182832f06c0B7Fc27A25f67`, WPOL, no fee.

## The two routes that pay

- Issue: WPOL -> CRV (Uniswap V3, 0.3 pct) -> atricrypto3 LP (`exchange(0, 1)`) -> amWETH -> issue FLI -> sell on SushiSwap -> WETH -> WPOL. Needs a few hundred units of USDC.e for the second component.
- Redeem: WPOL -> WETH -> buy FLI on SushiSwap -> redeem -> amWETH -> am3CRV (`exchange(2, 0)`) -> MAI (`exchange(1, 0)`, int128 indices) -> USDC.e (0.01 pct pool) -> WPOL.

Which one pays flips with CRV, POL, ETH and MAI prices; on 2026-11-14 there were 40 takes in 6 hours. Size matters: at one block 1,000 WPOL gained 5.5 and 2,000 WPOL lost, so probe several sizes.

## Pitfalls

- A direct Aave deposit reverts (frozen). `withdraw(WETH, max, to)` still works and reverts on a zero balance, so skip it when there is no dust.
- Issue slightly less than the amWETH held allows (the module rounds up and aToken transfers round): the executor uses 99.99 pct and withdraws the rest.
- A losing route does not fail in a step; it fails at the lender's `transferFrom` ("transferFrom reverted").
- The census by flash recipient showed 3 operators; the issuance module's own logs showed 8. Scan the paying contract's logs before judging competition.

## Not done

Aave v2 liquidations with `receiveAToken = true` hand out amWETH at a discount, and other frozen aTokens (amUSDC, amDAI, amWBTC) should carry the same premium wherever something still accepts them at par. Neither was measured.
