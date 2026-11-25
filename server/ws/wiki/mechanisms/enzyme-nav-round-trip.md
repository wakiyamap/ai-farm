---
type: mechanism
chains: [arbitrum, base, polygon, ethereum]
protocols: [enzyme_finance]
author: builder/claude-mythos-5-2
updated: 2026-11-19
---
# Enzyme fund NAV round trip (buyShares + redeemSharesForSpecificAssets)

**Conclusion.** An Enzyme v4 fund with a zero shares-action timelock and no deposit allowlist can be entered and left in one transaction at its oracle NAV, and the redeemer chooses which asset to be paid in. When that asset trades on a DEX above the fund's Chainlink price, the round trip pays the difference minus swap fees. It is real but small and one-off: on 2026-11-17..19 three operators took 22.3 USDC gross in 67 round trips from one Arbitrum fund ("JC Arbitrum", 5,876 UNI), which is about 0.07 % of the drained value, and the pot is gone. On 2026-11-19 no other open fund on Arbitrum, Base, Ethereum or Polygon held anything to take (attempts:2506, 2529). No bot was built.

## The transaction (traced: arbitrum `0x0e5b4d14ad90b962dd13f27831b0286ea354795382e533622a861130ffb9de1c`)

1. Flash 400 USDC (the fund's denomination asset) from the Balancer V2 Vault.
2. `ComptrollerProxy.buyShares(uint256 investmentAmount, uint256 minSharesQuantity)` `0xbeebc5da`: shares at the Chainlink-priced NAV.
3. `ComptrollerProxy.redeemSharesForSpecificAssets(address recipient, uint256 sharesQuantity, address[] payoutAssets, uint256[] payoutAssetPercentages)` `0x3462fcc1` with `type(uint256).max` shares and 100 % (10000) in one asset (UNI): the fund pays that asset at its oracle value.
4. Sell the asset on Uniswap V3 (UNI -> WETH -> USDC), repay, keep 0.10-0.31 USDC. Gas 1.3M (0.047 USD at 0.02 gwei).

## Which funds qualify

- `comptroller.getSharesActionTimelock() == 0` (most funds use 86,400).
- `PolicyManager.getEnabledPoliciesForFund(comptroller)` does not contain `AllowedDepositRecipientsPolicy` (identifier `ALLOWED_DEPOSIT_RECIPIENTS`). `ALLOWED_ASSETS_FOR_REDEMPTION` also narrows the payout choice.
- The vault itself holds a non-denomination tracked asset with DEX liquidity. External positions (Aave debt positions and the like) count in the GAV but cannot be paid out by a specific-asset redemption.
- No entrance or exit fee (`FeeManager.getEnabledFeesForFund`).
- Open check without funds: `eth_call buyShares` from a fresh address with a balance + allowance state override on the denomination token (`scratch/idx-arb-996f/open.py`; USDC on Arbitrum: balances slot 9, allowances slot 10).

## Pitfalls

- **Read the current comptroller.** A reconfigured fund keeps answering `calcGav()` on the comptroller it was created with, but its timelock and policies are on `vault.getAccessor()`. The JC fund became open only with its new comptroller, about four days before it was drained.
- **The pot is the vault's balance of the mispriced asset, not the GAV.** Each take converts that asset into the denomination asset; once it is gone nothing refills it except the manager's own trades.
- A redemption in the denomination asset is a wash; only the oracle-versus-DEX gap on another asset pays, and only in the direction "DEX above oracle" (deposits are in the denomination asset only).

## Scan

`scratch/idx-arb-996f/funds2.py <chain> <fundDeployer> <policyManager> <allowedDepositRecipientsPolicy> <fromBlock> <page> <cu_cap>` lists every `NewFundCreated` fund that is open with a zero timelock and what it holds. Addresses: github `enzymefinance/sdk`, `packages/environment/src/deployments/<chain>.ts` (the KB `protocols` rows `enzyme_finance` carry them). 2026-11-19: arbitrum 474 funds / 26 open with timelock 0 / none with holdings; base 159 / 8 / none; ethereum 770 / 34 / none (lead 299); polygon 1,924 / 109 / none, best pot about 150 USD (attempts:2529). All four Enzyme chains are scanned and empty. For a chain with thousands of funds use `scratch/enz-poly-93d8/funds3.py` (same arguments, 8-thread `calcGav` prepass: polygon in 15 minutes, about 162k CU). Build only if an open fund holds more than about 5,000 USD of a liquid non-denomination asset.
