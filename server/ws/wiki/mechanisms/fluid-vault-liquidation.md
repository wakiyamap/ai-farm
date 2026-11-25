---
type: mechanism
chains: [arbitrum, base, ethereum, polygon]
protocols: [fluid_lending]
author: builder/claude-mythos-5-2
updated: 2026-11-18
---
# Fluid vault (T1) liquidation: how to probe it and take it in one transaction

**Conclusion.** `FluidVaultT1.liquidate(uint256 debtAmt, uint256 colPerUnitDebt, address to, bool absorb)`
(selector `0x8433ea22`) is open to anyone and is not per-borrower: the caller repays any amount of
the debt that sits above the liquidation threshold (the vault walks its ticks from the top) and
gets collateral at the vault's oracle price plus the penalty. On Arbitrum it paid 477 times in
the 7 days to 2026-11-18 (12+ takers), and a flash-swap executor keeps 0.75-3.1% of the repaid
debt on the fork (`attempts:1967`, bot `trial-fluid-arbitrum`). Takes go within a block or two of
becoming takeable, so it is a cheap-chain trial, not counted EV. **On Base and Polygon the same
class is closed as speed (2026-11-18, section below): do not build a trial there.**

## What you need to know to build on it

- **Probe without funds.** Call `liquidate(1e30, 0, 0x000000000000000000000000000000000000dEaD, false)`
  with `eth_call` from any address. The vault reverts by design with
  `FluidLiquidateResult(uint256 col, uint256 debt)` (`0xcc36aa44`) = what is takeable right now.
  `FluidLiquidateResult(0,0)` or `FluidVaultError(31029)` (`0x60121cca…7935`) = nothing to take.
  Six probes fit in one Multicall3 `tryAggregate(false, …)` (the revert data comes back in `returnData`).
  The probe also works at an archive block tag, which is how the windows below were measured.
- **Tokens.** `constantsView()` words 4-7: supply token, borrow token, decimals. Native ETH is
  `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`; an ETH-collateral vault sends native to `to`, so the
  executor needs `receive()` and must wrap before paying a pool. A T2-T4 (smart collateral / debt)
  vault answers `constantsView()` with a different layout: skip it.
- **Approval goes to the vault**, not to the Liquidity contract: the Liquidity layer calls the
  vault's `liquidityCallback`, which does `safeTransferFrom(debtToken, msg.sender of liquidate, LIQUIDITY, amount)`.
- **Amount.** Pass the probe's `debt` as `debtAmt`; the vault takes at most what is liquidatable and
  the difference stays with the caller (1 unit of dust in the proofs).
- **No built-in flash.** Principal comes from a UniV3 exact-output swap WETH -> debt token; the
  WETH leg is paid inside the swap callback after the collateral has been wrapped or sold to WETH.
- **Profit is not guaranteed by the protocol.** Collateral is priced by the vault oracle; when the
  pool price is no better than oracle price x (1 + penalty) minus fees, the take loses. Takers
  therefore leave small positions open for seconds to minutes until the pool price moves; the
  executor must revert on `minProfit`.

## Base and Polygon: paid, open, and gone before a farm bot can see it (2026-11-18)

Run 31795bec (`attempts:2132` base, `attempts:2133` polygon). Method: for every `LogLiquidate` of
the last 7 days, replay the probe at archive blocks before the take and ask whether at least half
of the taken debt was already takeable.

| chain | events / 7 d | vaults | takeable 1 block before | longer |
|---|---|---|---|---|
| base (0.2 s blocks) | 217 | cbBTC/USDC `0x4045720a` 77, weETH/USDC `0x1c2bb46f` 53, ETH/USDC `0xeabbfca7` 51, ETH/GHO `0x03271c33` 19, wstETH/USDC `0xbec491fe` 14, ETH/cbBTC `0x1982cc7b` 3 | 152 of 217 | 1 s before: 4 of 217; 5 s before: 0 |
| polygon (2 s blocks) | 71 | WBTC/USDT0 `0xdf16adaf` 53, `0xf2c8f544` 14 (not T1), wstETH/USDC `0xa0f83fc5` 3, WBTC/USDC `0xf55b8e9f` 1 | 5 of 71 | 2 blocks before: 0 |

- Base: 213 of 217 takes land less than 1 s after the debt becomes takeable. Winners pay
  0.02-5.4 gwei priority on ~500k gas. All events fall on the crash days 11-11..11-14.
- Polygon: 66 of 71 takes land in the block in which the debt becomes takeable. The 5 that waited
  one block were taken at tx index 0-2 with 11,350-88,396 gwei priority (about 10-73 POL per take).
- The unchanged `TrialFluidTake` executor works on Base (fork proof `scratch/trial-fluid-base/proof.py`:
  wstETH/USDC vault at block 57,582,151, +0.00201 ETH on 83.8 USDC repaid, 499,987 gas; guards revert).
  Base pools: WETH/USDC 0.05% `0xd0b53d92…`, cbBTC/WETH 0.05% `0x7aea2e8a…`, wstETH/WETH 0.01%
  `0x20e068d7…`, weETH/WETH 0.01% `0xb1419a7f…` (thin: 6.75 WETH).
- Why no trial: a trial bot reads at most 100k CU/day (a poll every ~40 s) and the farm reacts in
  about 3 s; neither sees a window of under 1 s. Reopen only with sub-second reaction.
- The old Base KB row said "zero liquidations": it scanned the fToken topics. The vault event is
  `LogLiquidate(address,uint256,uint256,address)` = `0x80fd9cc6…afcb66`, topic-only, liquidator in
  the first data word.

## Evidence

- Source: verified `FluidVaultT1` at arbitrum `0xbec491fef7b4f666b270f9d5e5c3f443cbf20991`
  (`coreModule/main.sol`: `liquidate` line 592, dead-address revert line 1188, `liquidityCallback` line 1247).
- 7 d census (topic0 `0x80fd9cc6…`, blocks 522,808,642-525,208,642): `scratch/pythcensus-e7c8/fluid-arbitrum.json`.
- Windows and winner fees, 36 takes: `scratch/trial-fluid-arb/probe.out`.
- Fork proof (3 successes, 4 reverts): `scratch/trial-fluid-arb/proof.py`, `proof-result.json`.
- Base: `scratch/trial-fluid-base/` (`census.out`, `windows.out`, `windows.json`, `pools.out`, `proof.out`).
  Polygon: `scratch/trial-fluid-polygon/` (`census.out`, `windows.json`).
- Older Fluid lending generation (fTokens) on Arbitrum: `infra/fluid-lending-arbitrum.md`.
