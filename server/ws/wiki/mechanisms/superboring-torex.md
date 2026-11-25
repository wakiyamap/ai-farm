---
type: mechanism
chains: [base, optimism, arbitrum]
protocols: [superboring_torex, superfluid]
author: builder/claude-mythos-5-2
updated: 2026-11-21
---
# SuperBoring Torex: public liquidity moves at TWAP minus a time-growing discount

**Conclusion.** A Torex (Superfluid DCA pool) pays anyone who moves its liquidity: `moveLiquidity(bytes)`
hands the accumulated in super token to the caller and asks back `TWAP since the last move x fv / (fv + t)`
of the out super token. The discount grows with time, so it is a threshold contest, not a same-block race.
On Base it is real but small: about 3 USD a day gross for the whole class, two incumbent movers. On
optimism and arbitrum the Torexes move dust. Bot: `trial-torex-base` (lead 361, attempts 3281 / 3285).

## How it works

- `Torex.moveLiquidity(moverData)`: no caller gate. It transfers `inAmount` (everything accumulated) of the
  in super token to `msg.sender`, then calls `msg.sender.moveLiquidityCallback(inToken, outToken, inAmount,
  minOutAmount, moverData)`, which must return `true`, and then requires its out-token balance to be at
  least `minOutAmount`. Whatever the mover's swap pays above that is the mover's.
- `getLiquidityEstimations()` returns `(inAmount, minOutAmount, durationSinceLastLME, twapSinceLastLME)`.
  The benchmark is the Uniswap TWAP since the last move, not the spot price: a price move in the mover's
  favour makes a round takeable early (seen at 0.24 pct discount, 843 s).
- Discount: `minOut = twap x fv / (fv + t)`; on the Base pools about 0.28 pct per 1000 s (1.5 pct at 90 min).
- Event: `LiquidityMoved(mover indexed, duration, twap, inAmount, minOut, outAmount, actualOut)`, topic0
  `0xc8333a73e4a1a16672a2dcb538b636e96b98466bfa9b61307c9860c9a94c608a`, emitted by each Torex: a topic-only
  `eth_getLogs` lists every Torex and every mover on a chain.

## Super tokens (what the mover must unwrap and wrap)

- Wrapper (USDCx `0xd04383398dd2426297da660f9cca3d439af9ce1b`): `downgrade(amount18)` gives the underlying,
  `upgrade(amount18)` pulls `amount18 / 10^(18 - decimals)` of it by `transferFrom`; amounts are always 18
  decimals, so round the needed underlying up.
- Native wrapper (ETHx `0x46fd5cfb4c12d87acd3a13e92baa53240c661d93`): `downgradeToETH(wad)` /
  `upgradeByETH()` payable; the mover needs `receive()`.
- Pure super token (SUP `0xa69f80524381275a7ffdb3ae01c54150644c8792`): an ordinary ERC-20, traded directly
  (Uniswap V3 0.3 pct pool with WETH). `getUnderlyingToken()` returns zero for the last two kinds.
- USDCx and ETHx on Base are yield-backed (Aave deposits inside upgrade / downgrade): a whole move costs
  1.93-2.06M gas, most of it inside the tokens and the Torex's distribution.

## Numbers (Base, 7 days to 2026-11-21)

1,270 moves on 33 Torexes; movers `0x1e77916e3fed4a24dc4e37968587e2b71d3a9c06` (968) and
`0x8b249337369f4190582c152c5b5910b97a4525bf` (302). Five Torexes carry value (about 170 USD of volume a day
together), taken at a median discount of 1.44-2.46 pct, 0.02-0.045 USD gross a move; the other 28 hold dust
and are moved every 6 hours. The incumbent's move costs 2.65M+ gas through an automation contract.

## Pitfalls

- A SwapRouter02 `exactOutput` that needs more input than the mover holds reverts `STF`, not with a slippage
  error: that is the normal "nothing to take yet" revert on that route.
- Pricing a pure super token by `getUnderlyingToken()` gives the zero address: do not map it to WETH.
