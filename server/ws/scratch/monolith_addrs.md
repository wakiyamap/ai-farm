> ## Documentation Index
> Fetch the complete documentation index at: https://docs.monolith.market/llms.txt
> Use this file to discover all available pages before exploring further.

# Contract Addresses

> Deployed Monolith contract addresses

Monolith consists of a small set of singleton contracts per chain, plus per-instance `Lender`, `Coin`, and `Vault` contracts deployed by a `Factory`. There are two Factory deployments on mainnet (**V1** and **V2**). New markets deploy through **V2**. Optional per-market **DAO** governance is deployed by the DAO Factory (on-chain: CoinDAOFactory), which is wired to the V2 Monolith Factory.

## Singletons

### Ethereum Mainnet

#### Monolith Factories

| Contract | Address |
| - | - |
| Factory (V2, current) | [`0xc68F3e777f28c52FF9DB0276a14F59D96Aa2f931`](https://etherscan.io/address/0xc68F3e777f28c52FF9DB0276a14F59D96Aa2f931) |
| Factory (V1, previous) | [`0x6D961c9DCF1AD73566822BA4B087892e3839B849`](https://etherscan.io/address/0x6D961c9DCF1AD73566822BA4B087892e3839B849) |
| Lens | [`0x0f3a7cd1828698D2B6daEf081d5c319c0734fA1c`](https://etherscan.io/address/0x0f3a7cd1828698D2B6daEf081d5c319c0734fA1c) |
| Metadata | [`0x2Afb125bB848049b54D0903A1fd365E7518f581A`](https://etherscan.io/address/0x2Afb125bB848049b54D0903A1fd365E7518f581A) |
| Interest Model (V2) | [`0x77Fb136ed844dF83Bac1Bd6B87B0930764d5Ad6D`](https://etherscan.io/address/0x77Fb136ed844dF83Bac1Bd6B87B0930764d5Ad6D) |

Lens and Metadata are shared across V1 and V2 on mainnet. Each Factory has its own InterestModel. For V1, read the address with `factory.interestModel()`.

| Role | Address |
| - | - |
| V2 Deployer | [`0x11EC78492D53c9276dD7a184B1dbfB34E50B710D`](https://etherscan.io/address/0x11EC78492D53c9276dD7a184B1dbfB34E50B710D) |
| V2 Operator (also Monolith beneficiary for DAO Factory) | [`0x926dF14a23BE491164dCF93f4c468A50ef659D5B`](https://etherscan.io/address/0x926dF14a23BE491164dCF93f4c468A50ef659D5B) |

#### DAO Factory

User-facing name: **DAO**. On-chain the factory contract may still be named CoinDAOFactory.

| Contract | Address |
| - | - |
| DAO Factory | [`0x02A5F862e7aAD164Aa570Da15384d2563F3B9f4A`](https://etherscan.io/address/0x02A5F862e7aAD164Aa570Da15384d2563F3B9f4A) |
| Monolith Factory used | V2 [`0xc68F3e777f28c52FF9DB0276a14F59D96Aa2f931`](https://etherscan.io/address/0xc68F3e777f28c52FF9DB0276a14F59D96Aa2f931) |
| Monolith beneficiary | [`0x926dF14a23BE491164dCF93f4c468A50ef659D5B`](https://etherscan.io/address/0x926dF14a23BE491164dCF93f4c468A50ef659D5B) |
| GOV implementation | [`0xD513eF3fcFCD70713dd9Ff0bB8529AdD9617905D`](https://etherscan.io/address/0xD513eF3fcFCD70713dd9Ff0bB8529AdD9617905D) |
| Staked GOV implementation | [`0xfDC6911008293cf7c4eb19C8b3d09bB4AC09292D`](https://etherscan.io/address/0xfDC6911008293cf7c4eb19C8b3d09bB4AC09292D) |
| Revenue router implementation | [`0x97b9F65ceeC1FAB589AEab57eE6f24E3969f2De6`](https://etherscan.io/address/0x97b9F65ceeC1FAB589AEab57eE6f24E3969f2De6) |
| Staking rewards implementation | [`0xeb6d7a7622C5DADa310985F3a5A3811AdE458176`](https://etherscan.io/address/0xeb6d7a7622C5DADa310985F3a5A3811AdE458176) |
| Rewards funder implementation | [`0x9368A3f9526A71Af5B865d1be1a6e66CceDbaBbc`](https://etherscan.io/address/0x9368A3f9526A71Af5B865d1be1a6e66CceDbaBbc) |
| Vesting wallet implementation | [`0xa660016B9B6aDcd6dBBB0773ECf717fB229542CF`](https://etherscan.io/address/0xa660016B9B6aDcd6dBBB0773ECf717fB229542CF) |
| Governor implementation | [`0xF56A51085904581f145B410d6FbDe41293171010`](https://etherscan.io/address/0xF56A51085904581f145B410d6FbDe41293171010) |
| Timelock implementation | [`0x11f6C82F848030184D707456232789AAF13A65cB`](https://etherscan.io/address/0x11f6C82F848030184D707456232789AAF13A65cB) |

The DAO Factory and implementations above were redeployed on Oct 22, 2026. The previous DAO Factory (`0x5e30cfa382231d5c6952E0Ef333d191730e8e389`) has no DAO deployments and should not be used.

Per-DAO instances are EIP-1167 clones (CREATE2) of these implementations. Factory and implementation contracts are verified on Sourcify; Etherscan source verification may still be pending for some addresses.

### Sepolia Testnet

| Contract | Address |
| - | - |
| Factory (current) | [`0x8dDCaeb76a70b860DEaD944970bae0e955c10DA2`](https://sepolia.etherscan.io/address/0x8dDCaeb76a70b860DEaD944970bae0e955c10DA2) |
| Lens | [`0xf4DddA5149b482daF29f358986aFbA10A286116a`](https://sepolia.etherscan.io/address/0xf4DddA5149b482daF29f358986aFbA10A286116a) |
| Metadata | [`0x8aAb59675e123cEEFE5E05B0BC1bE8fe6101E60d`](https://sepolia.etherscan.io/address/0x8aAb59675e123cEEFE5E05B0BC1bE8fe6101E60d) |
| DAO Factory | [`0xD48f0c7D7d2F24367f71DC00Cf9d8f5157eeCCca`](https://sepolia.etherscan.io/address/0xD48f0c7D7d2F24367f71DC00Cf9d8f5157eeCCca) |

Sepolia UI currently exposes a single current Factory (no separate V1 entry). Use the address above for new testnet markets and DAO launches.

## Discovering per-instance contracts

Each stablecoin instance consists of three contracts deployed by `Factory.deploy(DeployParams)`:

* **Lender** - core lending contract for the instance
* **Coin** - ERC‑20 stablecoin for the instance
* **Vault** - ERC‑4626 staked vault for the instance

New markets are created on the **V2** Factory. The DAO Factory also uses the V2 Monolith Factory when launching a market together with a DAO. The V1 Factory remains for markets that were deployed there (notably **invUSD** on mainnet).

Enumerate existing instances by reading the relevant Factory:

```solidity theme={null}
uint256 count = factory.deploymentsLength();
address lender = factory.deployments(i);      // i < count
address coin   = address(Lender(lender).coin());
address vault  = address(Lender(lender).vault());
```

Or index the `Deployed(address indexed lender, address indexed coin, address indexed vault)` event emitted by the Factory on each `deploy()` call.

## Interest model

Each `Factory` deploys its own `InterestModel` in the constructor. Read it from that Factory:

```solidity theme={null}
address interestModel = factory.interestModel();
```

On mainnet, the V2 Interest Model address is listed in the table above. For V1, call `interestModel()` on the V1 Factory.

## Source code

All contracts are open source at [github.com/MonolithMarket/Monolith](https://github.com/MonolithMarket/Monolith).


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.