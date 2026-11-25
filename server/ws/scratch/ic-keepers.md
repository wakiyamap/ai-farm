> For the complete documentation index, see [llms.txt](https://docs.indexcoop.com/index-coop-community-handbook/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://docs.indexcoop.com/index-coop-community-handbook/products/trade/fli-keeper-bot-integration.md).

# Leverage Token Keepers

## Overview

This document contains information on setting up a keeper bot to rebalance the FLI product.&#x20;

Similar to yVaults, off-chain keeper bots are required to ping the smart contracts to maintain the ETHFLI strategy. Under the hood, the smart contracts will calculate whether the FLI should lever or delever according to the methodology and execute rebalances in 1 transaction via DEXs (initially Sushiswap or Uniswap).

There is an emergency delever function built in that will **reward the caller with 1 ETH** if leverage ratio goes above 2.7x in the ETH2x-FLI or 2.4x in the BTC2x-FLI. Scroll to the `ripcord()` section below for information on integrating.

For a technical introduction of the FLI system, view the slide deck [here](https://docs.google.com/presentation/d/1oQcuKkcyNWZ7nO-IqY-tk9h3Vb4_lktX0AyfEwdxDNs/edit#slide=id.g38420732af_0_142).

If you have any questions, join the `#dev` channel in our [Discord](https://discord.com/invite/ezuJ6ZZ).

## **Mainnet Production Addresses**

View the latest contract addresses [here](broken://pages/-MLpfEEcyAvV2d5-6fEC).

## **Integration**

All keeper interactions will be through the FlexibleLeverageStrategyAdapter contract ([ABI](https://gist.github.com/richardliang/1c015c90f98faa41bbb6a359c6b928c7)).&#x20;

![](https://lh6.googleusercontent.com/zTEHC14rV6sAqPeZYSHzuI_-e4Ny13WUfCRts16zyGBXm_o39aa4lLnOuAXVdT5xWRe1_Jb5RHZROCGPdkZ2MkiSkt6Ww_G8myLsYurDd_22YBRGiT6uGUOQjGrMhlzRbDt9T0hu)

On the strategy contract, there are 4 external getter functions that keepers can monitor:

1. **shouldRebalance()**
   1. Interface: function shouldRebalance() external view returns(string\[], ShouldRebalance\[])
   2. Helper that checks if conditions are met for rebalance or ripcord. Returns a tuple of exchange name strings and enums with 0 = no rebalance, 1 = call rebalance(), 2 = call iterateRebalance(), and 3 = call ripcord()
2. **shouldRebalanceWithBounds()**
   1. Interface: function shouldRebalanceWithBounds(uint256 \_minLeverageRatio, uint256 \_maxLeverageRatio) external view returns(string\[], ShouldRebalance\[])
   2. Similar to shouldRebalance, this is a helper that checks if conditions are met for rebalance or ripcord. Returns a tuple of exchange names and enums with 0 = no rebalance, 1 = call rebalance(), 2 = call iterateRebalance(), and 3 = call ripcord()
   3. Allows keeper bots to customize the min and max bounds to call rebalance. For example, you may not want to call at slightly above max leverage every time 2.31x leverage every time
3. **getCurrentLeverageRatio()**
   1. Get current leverage ratio. Current leverage ratio is defined as the USD value of the collateral divided by the USD value of the SetToken. Prices for collateral and borrow assets are retrieved from the Compound Price Oracle.
   2. This function may be needed to toggle the threshold for calling rebalance() if the current leverage ratio goes above the max bound or below the min bound. E.g. if leverage ratio is 2.31x, shouldRebalance will return 1, but we may not need to call rebalance() to bring it to 2.3x leverage. Instead, keepers may wait until 2.4x or higher to save on gas.
4. **getCurrentEtherIncentive()**
   1. Get current Ether incentive for when current leverage ratio exceeds incentivized leverage ratio and ripcord can be called. If ETH balance on the contract is below the etherReward, then return the balance of ETH instead. If not above the ripcord threshold, then it returns 0

Depending on which enum **shouldRebalance** returns, keepers will need to call the appropriate function:

1. **rebalance()**
   1. Should rebalance returns 1
   2. Pass in an exchange name string. The exchange must be enabled on the adapter
   3. Only whitelisted addresses can call. Only EOA
   4. This is a regular rebalance according to the FLI methodology. If within the max and min leverage ratios, rebalances will only happen every 24 hours. If outside those bounds, keepers can call rebalance anytime to bring it to the max or min leverage.
2. **iterateRebalance()**
   1. Should rebalance returns 2
   2. Pass in an exchange name string. The exchange must be enabled on the adapter
   3. Only whitelisted addresses can call. Only EOA
   4. This follows a rebalance() call only if the total notional trade size is greater than the max trade size or max borrow limit. This iterates through the TWAP and can be called every 30 sec until the notional amount is rebalanced
3. **ripcord()**
   1. Should rebalance returns 3
   2. Pass in an exchange name string. The exchange must be enabled on the adapter
   3. Anyone can call, not just whitelisted addresses. Only EOA. This can only be called if the current leverage ratio is above the threshold (2.7x initially). This function typically would only be called if keeper bots have not been able to call rebalance() between 2.3x and 2.7x leverage.&#x20;
   4. There is no TWAP when above the ripcord threshold (2.7x). Only need to continuously ping this function until we get below 2.7x
   5. Ripcord will use its own settings for slippage tolerance (5%), cooldown period (1 sec), and max trade size (1200 ETH)
   6. **Caller is rewarded with 1 ETH**
4. **Do nothing**
   1. Should rebalance returns 0

**Note:** In the initial guarded launch, there will be a whitelist of addresses allowed to call the **rebalance()** and **iterateRebalance()** functions. Therefore, any keeper addresses need to be whitelisted prior to launch or go through Index Coop governance post launch. **Ripcord()** does not have this restriction, and will be callable by anyone.

Below are the estimated gas costs for calling each of the 3 functions above:

| **Parameter**         | **Gas Cost** |
| --------------------- | ------------ |
| **Rebalance**         | **\~625k**   |
| **Ripcord**           | **\~665k**   |
| **Iterate rebalance** | **\~614k**   |

## **Resources**

* [FlexibleLeverageStrategyAdapter ABI](https://gist.github.com/richardliang/1c015c90f98faa41bbb6a359c6b928c7)
* [Contract addresses](broken://pages/-MLpfEEcyAvV2d5-6fEC)
* [Discord](https://discord.com/invite/ezuJ6ZZ)
