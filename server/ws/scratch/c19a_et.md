---
type: method
chains: [base, arbitrum, ethereum, bsc, polygon, avalanche, optimism, hyperevm, elysium]
protocols: [any]
author: meta/opus
updated: 2026-11-14
---
# Executor techniques: read rival executor contracts, list what farm should adopt (decision 2026-11-14-crash-postmortem-rival-contracts, part 2)

**Conclusion first:** earners read the executor contracts of the operators that earn most, compare gas against farm's executor on the same case on the fork, and list each technique found as one row in the table at the end, with its evidence tx and its measured effect ("unmeasured" if no number). Meta forwards the top 5 to the human (title `executor-techniques`); the human decides whether farm's common executor design changes. A tip the human heard: "put the gas accounting inside the contract" - confirm or refute it from real code. Source: the decision file (Japanese; it wins if this page disagrees).

## Targets (researcher picks, earner reads)

- executors of the top 5 operators by gross in the census (`infra/liquidator-census.md`)
- takers with many cases or high gross in the crash post-mortem that are not in that 5 (at most 5)
- from `infra/bot-census/`: any operator, any class, whose executor uses clearly less gas or fails less than farm's
- the current queue is on `infra/crash-2026-11-14.md` (2-1)

## How to read (earner)

- Verified source from a keyless public place if it exists. Otherwise follow successful and failed txs with `fork replay` / `fork trace` / `debug_traceTransaction` and write down what it calls in which order.
- Make farm's executor take the same case on the fork at the parent block and **put the gas used side by side**. Find where the difference comes from.

## What to note per contract (only what you found, each with a tx hash; "unknown" is fine)

- **Entry**: one selector or packed calldata, calldata size, who may call
- **Funding**: flash loan or flash swap, from where, fee; own inventory
- **Exit**: where and into what the collateral is sold; route fixed in the contract or passed in calldata
- **Profit guard**: in which token; **does it subtract gas inside the guard** (reads `tx.gasprice` / `block.basefee`, or the OP-stack L1 fee from `GasPriceOracle` 0x420...0F, and compares with expected profit)
- **Cheap miss**: when already taken, where it stops; gas of failed / no-op txs vs farm's executor revert
- **Priority fee**: fixed or scaled with profit; any `block.coinbase` transfer (builder bundle = class D sign)
- **Batching**: several liquidations per tx
- **Where profit stays**: in the contract or sent to the EOA, in which token
- **Taker type** of its cases (`methods/taker-types.md`)

Write a "Contract" section on the operator's card `infra/bot-census/<operator>.md`.

## Do not

- Send any tx to a rival's contract on mainnet. Read public code and txs; test only on the fork.
- Use a flaw in a rival's contract (anyone-callable withdraw, missing access control, a drain path) on mainnet, ever. Reproduce it **on the fork only**, write only "flaw found" on the card, and report the details to `inbox/human/` titled `rival-contract-finding`: contract address (chain, deployer if known), the flaw, the fork tx that shows it, rough amount at risk.
- Copy source verbatim. Understand the mechanism and implement it in farm's executor.
- Find out who owns an address.

## Techniques found (earners add one row each; researcher ranks)

| # | technique | evidence tx | effect if farm adopts it (gas, miss cost, cases gained) | effort | rank |
|---|---|---|---|---|---|
| 1 | Atlas solvers read the OP-stack L1 fee (`GasPriceOracle` 0x42..0f) and refund gas in ETH inside the tx: full gas accounting in the contract (from `infra/bot-census/atlas-oev-solvers.md`, trace on `infra/pull-oracle-markets.md` base morpho row) | `0x8fd693c4cd929bc708f1d7e812e9acc85702018b79689201ea8fdf48cabf2b96` (base) | unmeasured | unmeasured | - |
| 2 | Batch up to 41 liquidations in one tx (d128): implementation self-calls the proxy per position (vanity selector 0xbbbbbbbb, 165-byte packed calldata each), amortizing entry, exit swap and Atlas fee over the batch; per-iteration self-call averaged 88,039 gas, batch total 5,061,760 (~123.5k/liquidation amortized). Farm's one-per-tx executor would cut entry/exit gas per liquidation at the cost of a bigger miss (from `infra/bot-census/op-d12810b1.md`) | `0xd96c090d6955e28f699157ff4e41cc1a2c1123633053f76822c790a74afbde5f` (base, 41 events) | batched gas measured; farm gain unmeasured | unmeasured | - |
| 3 | Cheap miss by preview-skip, not revert: each iteration pre-checks `previewRedeem` x3 on the debt token + `balanceOf`/`allowance` before Morpho `liquidate`; already-seized positions self-skip and the batch ends with status 1 (measured on the fork: same tx re-sent after the seizure = 525,090 gas, zero logs vs the 5,061,760-gas batch) (card `op-d12810b1.md`) | fork resend at block 57399504, base (replay 0xa8da9546d5d813d9cc6fb43e9378c02f92483d5be18e5c32dcfe78d56f4e3af0) | miss costs ~10% of a batch with no revert; farm revert-miss comparison unmeasured | unmeasured | - |
| 4 | Accrue inside the tx: `accrueInterest((MarketParams),...)` per position (33.9k gas) immediately before `liquidate`, so the repay amount is fresh with no pre-read of the accrual state (from card `op-d12810b1.md`) | `0xd96c090d6955e28f699157ff4e41cc1a2c1123633053f76822c790a74afbde5f` (base) | gas measured (33.9k/position); cases gained unmeasured | unmeasured | - |
| 5 | Morpho native repayment flow instead of a flash loan: `liquidate` pays the debt asset from the vault, `onMorphoLiquidate(uint256,bytes)` callback, then Morpho pulls the repay from the executor (transferFrom 9.2k); no external flash-loan fee in the trace. Exit converts leftover to gas once per batch via `topUpWeth(uint256)` + WETH `withdraw`, and the contract forwards the ETH to an operator wallet (0x1c6e...) - profit held as ETH outside the contract | `0xd96c090d6955e28f699157ff4e41cc1a2c1123633053f76822c790a74afbde5f` (base) | gas measured per trace; farm savings unmeasured | unmeasured | - |
