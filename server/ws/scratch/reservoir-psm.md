> For the complete documentation index, see [llms.txt](https://docs.reservoir.xyz/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://docs.reservoir.xyz/protocol-architecture/peg-stability-module.md).

# Peg Stability Module

The Peg Stability Modules (PSMs) are efficiently managed via the Credit Enforcer system, which auto balances the PSM to have enough liquidity needed to support demand on the respective chain, but not more than is needed and can be allocated elsewhere.

The USDC PSM is automated to maintain a minimum balance of 25 - 50 bps of total assets at all times, automatically refilling every hour.

The stablecoin peg is also stabilized via the credit enforcer, which is powered by the proof of reserves. It ensures that there is always enough USDC and USDT to redeem liquid rUSD. This will increase trust in the peg as users have a fully transparent view into health of the balance sheet.&#x20;

Another important aspect to the peg is the assets that collateralize the stablecoin protocol. All existing decentralized stablecoin protocols today are only able to use liquid DeFi assets. This presents peg ris&#x6B;*,* as large market participants can execute profitable strategies to push the price of digital assets down on the market and create insolvency risk. RWA collateral provides a significant differentiating factor not only in the form of higher yields, but also in how uncorrelated and more stable it is to the digital asset market.
