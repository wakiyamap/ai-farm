> For the complete documentation index, see [llms.txt](https://tech.usual.money/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://tech.usual.money/overview/features/mint-and-redeem-engine.md).

# Mint & Redeem Engine

## Overview

The mint and redeem engine of the Usual protocol, combines two smart contracts: **DaoCollateral** and **Swapper Engine**. These contracts work in tandem to manage the creation and redemption of USD0 and EUR0, stablecoins backed by Real World Assets (RWAs). Together, they ensure the full collateralization, while providing users with a seamless, non-custodial trading experience. This system is enhanced by an intent-based matching system and an order-matching mechanism, offering an efficient and transparent process for minting, redeeming, and swapping USD0, EUR0 with USDC and EURC respectively. The flows below display interactions, using USD0 as an example. Other Usual issued Stablecoins work similarly.

<details>

<summary><strong>Minting USD0 via DaoCollateral</strong></summary>

* A user who holds RWAs (represented as USYC tokens) interacts with the DaoCollateral contract to mint USD0 stablecoins
* The user sends USYC tokens to the DaoCollateral contract, which calculates the equivalent amount of USD0 at the current exchange rate
* USD0 is minted and provided to the user in exchange for their USYC tokens
* This ensures that every USD0 in circulation is backed by RWAs, providing stability and security

</details>

<details>

<summary><strong>Redeeming USD0 via DaoCollateral</strong></summary>

* Users who hold USD0 stablecoins can redeem them for RWAs (USYC tokens)
* The user invokes the redeem function, providing their USD0 to the DaoCollateral contract
* The contract calculates the equivalent value of USYC tokens based on the current exchange rate and sends these tokens to the user, burning the corresponding USD0 in the process

</details>

<details>

<summary><strong>Swapping USDC and USD0 via Swapper Engine</strong></summary>

* Users can create orders specifying the amount of USDC they want to swap for USD0 by depositing USDC into the Swapper Engine
* Other users can fill these orders by providing USD0, with the contract verifying their USD0 balance and allowance
* The contract relies on an external oracle to fetch the current USDC price, ensuring that swaps happen at accurate and fair exchange rates
* Partial or full matching of orders is allowed, depending on user preferences and order availability

</details>

<details>

<summary><strong>Three-Way Intent-Based Matching System</strong></summary>

* In a three-party trade facilitated by DaoCollateral, a **USDC provider**, an **RWA provider**, and the **DaoCollateral contract** come together
  * The **USDC provider** deposits USDC into the Swapper Engine and receives USD0 in return.
  * The **RWA provider**, who holds RWAs (USYC tokens), submits an intent to exchange these tokens for USDC
  * The DaoCollateral contract mints new USD0 in exchange for the RWAs from the RWA provider and uses this newly minted USD0 to fulfill the USDC provider’s order.
  * Finally, the contract transfers the USDC from the Swapper Engine to the RWA provider, completing the trade
* This intent-based matching system ensures efficient, non-custodial trading by allowing RWA providers to retain their assets until the trade is executed.

</details>

## Smart Contracts

{% content-ref url="/pages/9VSTNV5ffFhdsBG7JCjZ" %}
[USD0 Swapper Engine](/smart-contracts/protocol-contracts/usd0/usd0-swapper-engine.md)
{% endcontent-ref %}

{% content-ref url="/pages/cdEnoP1Vp2m1T0Lp8xc1" %}
[USD0 DaoCollateral](/smart-contracts/protocol-contracts/usd0/usd0-daocollateral.md)
{% endcontent-ref %}
