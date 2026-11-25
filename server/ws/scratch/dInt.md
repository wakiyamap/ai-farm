> For the complete documentation index, see [llms.txt](https://docs.maple.finance/llms.txt). Markdown versions of documentation pages are available by appending `.md` to page URLs; this page is available as [Markdown](https://docs.maple.finance/technical-resources/interfaces.md).

# Contract Interfaces

Reference pages for the external interface of every Maple contract, generated from the Solidity natspec and grouped by subsystem. Each page lists the contract's functions and events, the members it inherits from the proxy interfaces, and any structs or enums its functions use.

## Globals and Timelock

| Page                                                                     | Contract           | Module    |
| ------------------------------------------------------------------------ | ------------------ | --------- |
| [Globals](/technical-resources/interfaces/globals.md)                    | `MapleGlobals`     | `globals` |
| [GovernorTimelock](/technical-resources/interfaces/governor-timelock.md) | `GovernorTimelock` | `globals` |

## Pools

| Page                                                                                  | Contract                      | Module                    |
| ------------------------------------------------------------------------------------- | ----------------------------- | ------------------------- |
| [Pool](/technical-resources/interfaces/pool.md)                                       | `MaplePool`                   | `pool`                    |
| [PoolManager](/technical-resources/interfaces/pool-manager.md)                        | `MaplePoolManager`            | `pool`                    |
| [PoolManagerFactory](/technical-resources/interfaces/pool-manager-factory.md)         | `MaplePoolManagerFactory`     | `pool`                    |
| [PoolManagerInitializer](/technical-resources/interfaces/pool-manager-initializer.md) | `MaplePoolManagerInitializer` | `pool`                    |
| [PoolDeployer](/technical-resources/interfaces/pool-deployer.md)                      | `MaplePoolDeployer`           | `pool`                    |
| [PoolPermissionManager](/technical-resources/interfaces/pool-permission-manager.md)   | `MaplePoolPermissionManager`  | `pool-permission-manager` |

## Withdrawal Manager

| Page                                                                                                            | Contract                            | Module                     |
| --------------------------------------------------------------------------------------------------------------- | ----------------------------------- | -------------------------- |
| [WithdrawalManager (Queue)](/technical-resources/interfaces/withdrawal-manager-queue.md)                        | `MapleWithdrawalManager`            | `withdrawal-manager-queue` |
| [WithdrawalManagerFactory (Queue)](/technical-resources/interfaces/withdrawal-manager-queue-factory.md)         | `MapleWithdrawalManagerFactory`     | `withdrawal-manager-queue` |
| [WithdrawalManagerInitializer (Queue)](/technical-resources/interfaces/withdrawal-manager-queue-initializer.md) | `MapleWithdrawalManagerInitializer` | `withdrawal-manager-queue` |

## Open Term Loans

| Page                                                                                                    | Contract                      | Module                   |
| ------------------------------------------------------------------------------------------------------- | ----------------------------- | ------------------------ |
| [OpenTermLoan](/technical-resources/interfaces/open-term-loan.md)                                       | `MapleLoan`                   | `open-term-loan`         |
| [OpenTermLoanFactory](/technical-resources/interfaces/open-term-loan-factory.md)                        | `MapleLoanFactory`            | `open-term-loan`         |
| [OpenTermLoanInitializer](/technical-resources/interfaces/open-term-loan-initializer.md)                | `MapleLoanInitializer`        | `open-term-loan`         |
| [OpenTermLoanRefinancer](/technical-resources/interfaces/open-term-loan-refinancer.md)                  | `MapleRefinancer`             | `open-term-loan`         |
| [OpenTermLoanManager](/technical-resources/interfaces/open-term-loan-manager.md)                        | `MapleLoanManager`            | `open-term-loan-manager` |
| [OpenTermLoanManagerFactory](/technical-resources/interfaces/open-term-loan-manager-factory.md)         | `MapleLoanManagerFactory`     | `open-term-loan-manager` |
| [OpenTermLoanManagerInitializer](/technical-resources/interfaces/open-term-loan-manager-initializer.md) | `MapleLoanManagerInitializer` | `open-term-loan-manager` |

## Modular Strategies

| Page                                                                                          | Contract                          | Module             |
| --------------------------------------------------------------------------------------------- | --------------------------------- | ------------------ |
| [StrategyManager](/technical-resources/interfaces/strategy-manager.md)                        | `MapleStrategyManager`            | `strategy-manager` |
| [StrategyManagerFactory](/technical-resources/interfaces/strategy-manager-factory.md)         | `MapleStrategyManagerFactory`     | `strategy-manager` |
| [StrategyManagerInitializer](/technical-resources/interfaces/strategy-manager-initializer.md) | `MapleStrategyManagerInitializer` | `strategy-manager` |
| [StrategyDeployer](/technical-resources/interfaces/strategy-deployer.md)                      | `MapleStrategyDeployer`           | `strategy-manager` |
| [LiquidityRouter](/technical-resources/interfaces/liquidity-router.md)                        | `MapleLiquidityRouter`            | `strategy-manager` |

## Aave V3 Strategy

| Page                                                                                         | Contract                         | Module            |
| -------------------------------------------------------------------------------------------- | -------------------------------- | ----------------- |
| [AaveV3Strategy](/technical-resources/interfaces/aave-v3-strategy.md)                        | `MapleAaveV3Strategy`            | `defi-strategies` |
| [AaveV3StrategyFactory](/technical-resources/interfaces/aave-v3-strategy-factory.md)         | `MapleAaveV3StrategyFactory`     | `defi-strategies` |
| [AaveV3StrategyInitializer](/technical-resources/interfaces/aave-v3-strategy-initializer.md) | `MapleAaveV3StrategyInitializer` | `defi-strategies` |

## Sky Strategy

| Page                                                                                  | Contract                      | Module            |
| ------------------------------------------------------------------------------------- | ----------------------------- | ----------------- |
| [SkyStrategy](/technical-resources/interfaces/sky-strategy.md)                        | `MapleSkyStrategy`            | `defi-strategies` |
| [SkyStrategyFactory](/technical-resources/interfaces/sky-strategy-factory.md)         | `MapleSkyStrategyFactory`     | `defi-strategies` |
| [SkyStrategyInitializer](/technical-resources/interfaces/sky-strategy-initializer.md) | `MapleSkyStrategyInitializer` | `defi-strategies` |

## Allocation Strategy

| Page                                                                                                | Contract                             | Module                |
| --------------------------------------------------------------------------------------------------- | ------------------------------------ | --------------------- |
| [AllocationStrategy](/technical-resources/interfaces/allocation-strategy.md)                        | `MapleAllocationStrategy`            | `allocation-strategy` |
| [AllocationStrategyFactory](/technical-resources/interfaces/allocation-strategy-factory.md)         | `MapleAllocationStrategyFactory`     | `allocation-strategy` |
| [AllocationStrategyInitializer](/technical-resources/interfaces/allocation-strategy-initializer.md) | `MapleAllocationStrategyInitializer` | `allocation-strategy` |

## Peripheral

| Page                                                           | Contract      | Module        |
| -------------------------------------------------------------- | ------------- | ------------- |
| [SyrupRouter](/technical-resources/interfaces/syrup-router.md) | `SyrupRouter` | `syrup-utils` |


---

# Agent Instructions
This documentation is published with GitBook. GitBook is the documentation platform designed so that both humans and AI agents can read, navigate, and reason over technical content effectively. Learn more at gitbook.com.

## Querying This Documentation
If you need additional information that is not directly available in this page, you can query the documentation by asking a question.

Perform an HTTP GET request on the following URL with the `ask` and `goal` query parameters:

```
GET https://docs.maple.finance/technical-resources/interfaces.md?ask=<question>&goal=<user_goal>
```

`ask` is the immediate question: it should be specific, self-contained, and written in natural language.
`goal` is what the user is ultimately trying to achieve, the reason they need the answer. Sharing it helps GitBook give you a better, more relevant answer. A goal is most helpful when it describes the outcome the user wants rather than restating the question. For example, with `ask=how do I create an API token`, a goal like `automate deployments from our CI pipeline` lets GitBook tailor the answer to that use case.

The response will contain a direct answer to the question and relevant excerpts and sources from the documentation.

Use this mechanism when the answer is not explicitly present in the current page, you need clarification or additional context, or you want to retrieve related documentation sections.
