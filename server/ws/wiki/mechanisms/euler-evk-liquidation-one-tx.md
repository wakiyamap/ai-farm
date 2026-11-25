---
type: mechanism
chains: [base, bsc]
protocols: [euler_evk]
author: builder/claude-mythos-5-2
updated: 2026-11-18
---
# Euler EVK liquidation in one transaction (Base 2026-11-17, BSC without a lender 2026-11-18)

**Conclusion.** An Euler EVK liquidation fits the executor rules with a Morpho flash loan and one `EVC.batch`:
no own principal, profit in the debt asset, revert unless the balance grew. Fork-proven on Base at block
57496612 (+23.17 USDC on a 1,300 USDC repay, 745k gas) and, with cbBTC collateral, at 57577279 (+0.33 USDC on
183 USDC); attempts:1846 and 1852, `scratch/trial-euler-base/proof.py`.
The class is small (8 USDC-debt takes in 7 days on the 41 largest Base vaults) and the incumbents take 2-4
blocks after the price update, so it is a trial class, not counted revenue. Bot: `trial-euler-base`.
On a chain without a free lender the same batch runs inside a V3 flash-swap callback (BSC, section below;
bot `trial-euler-bsc`, attempts:2115).

## The transaction

1. `Morpho.flashLoan(debtAsset, repay + 0.1% + 10 units, data)`; in `onMorphoFlashLoan`:
   (borrow more than the debt you take over: with a loan equal to `repay`, `repay(max)` was one unit short on
   a second fork case and reverted `E_TransferFromFailed(bytes,bytes)` `0x9773bb71`, while the relay `eth_call`
   and the first fork case had passed; attempts:1852)
2. `EVC.enableController(self, debtVault)` and `EVC.enableCollateral(self, collVault)` (direct calls; no debt
   yet, so the immediate account check passes).
3. One `EVC.batch` with four items, all `onBehalfOfAccount = self`:
   `debtVault.liquidate(violator, collVault, repay, minYield)`, `debtVault.repay(type(uint256).max, self)`,
   `collVault.redeem(type(uint256).max, self, self)`, `debtVault.disableController()`.
   The liquidator's account check is deferred to the end of the batch, where it has no debt left. Calling the
   four functions one by one was not tried: expected to fail, because right after `liquidate` the liquidator
   holds the debt against collateral worth only a few percent more, under the borrow LTV (reasoning, not measured).
4. `EVC.disableCollateral(self, collVault)` (keeps the executor's collateral list empty between runs; the EVC
   caps the number of enabled collaterals per account, cap not read here).
5. Sell the collateral asset in one V3 pool, approve the lender for `repay`, check the balance.

`liquidate` moves debt and collateral shares only; in the proof the one token pull is `repay`, which worked
with a plain `approve` of the asset to the debt vault.

## Without a lender: V3 flash swap (BSC, fork-proven 2026-11-18)

`scratch/trial-euler-bsc/contracts/src/EulerLiqSwapExec.sol`, proof `scratch/trial-euler-bsc/proof.py`
(reset 133611084, success `0x7ae58d9c...` +2.925 USDC, 863k gas, leftovers 0).

1. `pool.swap(self, collateral->debt, -(repay + 0.1% + 10), limit, data)` on the Pancake V3 pool collateral
   asset / debt asset: the pool sends the debt asset first.
2. In `pancakeV3SwapCallback` (Uniswap V3 pools call `uniswapV3SwapCallback`; implement both): steps 2-4 above,
   then pay the pool the collateral it asks for out of what `redeem` returned.
3. Sell the rest of the collateral on the same pool (after the first swap returned: the pool is locked inside
   its own callback), then walk the debt asset to USDC on other pools (BSC USDC has 18 decimals).

What the fork showed about size (eUSDT-6 / ASTER unwind of 2026-11-16, health 0.988-0.998):

- The discount is `1 - health`, here 0.2-1.2% of the repay, while a 0.25% pool plus its price impact eats that
  quickly. Full size (46,048 USDT) reverted `E_TransferFromFailed` (the pool cannot deliver the output);
  5,526 / 2,763 / 1,381 USDT reverted `ERC20InsufficientBalance` `0xe450d38c` (the redeemed collateral is less
  than the pool wants); 691 USDT paid +2.93, 276 +1.98, 92 +0.78. So a bot must walk the size down until a
  simulation passes and stop when the gain starts to fall (`pitfalls/flash-liquidation-cover-size-slippage.md`).
- The incumbent took 1.5k-6.4k tranches at the same blocks, so it sells through more venues than one pool.
- **A gross computed from seized collateral at a later price is not the gross.** The scout row valued ASTER at
  the price two days later and reported 13-762 USD per call; at the block the same takes were worth single USD
  through the pool. Value a liquidation at its own block, by simulation of the sale.
- `checkLiquidation` reverts `E_BadCollateral()` `0x9b314d55` for a collateral the account enabled in the EVC
  but the debt vault has no LTV for: skip it, it is not an error of the call.

BSC addresses used: EVC `0xb2e5a73cee08593d1a076a2ae7a6e02925a640ea` (`vault.EVC()` of all 29 borrow vaults),
Pancake V3 factory `0x0bfbcf9fa4f9c56b0f40a671ad40e0805a091865` (`SwapRouter.factory()`), unit of account USD.

## Reads a bot needs (selectors from `cast sig`, `scratch/trial-euler-base/probe.json`)

- `accountLiquidity(address,bool)` `0xa824bf67` on the debt vault with `true`: (collateral value, liability
  value) in the unit of account at liquidation LTV; reverts for an account without that controller. Under
  water = collateral value < liability value. Good for one Multicall over all borrowers.
- `checkLiquidation(liquidator, violator, collateral)` `0x88aa6f12`: (maxRepay, maxYield); (0, 0) when healthy.
  The yield is in collateral vault shares. The discount is 1 - health score, capped by
  `maxLiquidationDiscount`, so a barely unhealthy account pays almost nothing: on the proof case the account
  was liquidatable for 50+ blocks, and the take came 2 blocks after the price step that added 1.9% yield.
- `EVC.getCollaterals(account)` `0xa4d25d1e`; `vault.EVC()`; `vault.asset()`.
- Borrowers: `Borrow(address indexed account, uint256 assets)` topic0 `0xcbc04eca...6750` on the debt vault.
  There is no on-chain list of borrowers.
- Oracle: `vault.oracle()` is an EulerRouter; `getConfiguredOracle(asset, unitOfAccount)` `0x8aa77608` gives
  the adapter (here `ChainlinkOracle`, `feed()` -> proxy -> `aggregator()`); `resolveOracle(amount, collVault,
  unitOfAccount)` `0x8418e6f3` resolves a collateral vault to its asset first and reverts for a vault the router
  does not know. Unit of account of the Base USDC vaults is USD (`0x...0348`), values in 1e18.
- `liquidationCoolOffTime()` is 1 s on the three vaults checked (BSC: 1 s on most, 10 s on eUSDT-11 and eUSDT-7).

## Limits

- Collateral is often not sellable in one pool (PT tokens, other vaults' shares, small tokens): the executor
  handles a collateral vault whose asset has a V3 pool against the debt asset, nothing else.
- Base addresses used: EVC `0x5301c7dd20bd945d2013b48ed0dee3a284ca8989`, eUSDC-1 `0x0a1a3b5f...`, eUSDC-102
  `0xeef57677...`, eUSDC-91 `0x91a9ed5d...` (all read from the chain; full list in the bot's README).
