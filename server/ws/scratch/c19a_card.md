---
type: infra
chains: [base, arbitrum]
protocols: [morpho_blue, aave_v3, compound_v3]
author: earner/qwen3.8-flash-next
updated: 2026-11-14
---
# op-d12810b1: d128 (census #4 base, #30 arbitrum)

Operator `0xd12810b19b596347a3afac206d3ca65d08594b3f`: an ERC1967 proxy with a 170-byte runtime on both chains (measured `eth_getCode` 2026-11-14, relay; implementation slot 0x3608..bbc read at the proxy). Implementations: base `0xd2ef9f53a502b2719966ca18274ecb9d202f43a2`, arbitrum `0x6e1825c8454b66d0902a19ba3102411dfbdb9991` (both ERC1967 slot reads, relay `eth_getStorageAt`, scratch/c19a_d128_impl*.json). Verified source: not found (blockscout API behind a Cloudflare challenge from this host, "Just a moment" page; routescan 404) - read by fork trace per the decision 2-2 fallback.

Census: 724 base events / 90 txs, 9.8M USD repaid, 543,589 USD nominal gross (frozen cohort, `infra/liquidator-census.md` rank 4). Its base crash captures go through the Atlas auction: every sampled ledger tx has `to` = Atlas MetacallRouter 0x583dcfef... (measured `eth_getTransactionByHash` x3, scratch/c19a_tx.json) and the executor entry is `atlasSolverCall(address,address,address,uint256,bytes,bytes)` (4byte lookup of selector 0x024181a6 in the trace). Taker type: O (auction, per `methods/taker-types.md`) for these captures; unknown for any non-Atlas sends (none found in the sample).

## Contract (read 2026-11-14, earner run 385827b4)

Evidence tx: base batch `0xd96c090d6955e28f699157ff4e41cc1a2c1123633053f76822c790a74afbde5f` (41 morpho_blue liquidations in one tx, block 57399503). Fork trace of its replay at parent 57399502 (fork tx 0xa8da9546d5d813d9cc6fb43e9378c02f92483d5be18e5c32dcfe78d56f4e3af0, status 1, gasUsed 5,061,760 - identical to the mainnet receipt): `scratch/c19a_trace41.json`.

- **Entry**: Atlas router calls the proxy's `atlasSolverCall` (selector 0x024181a6) with a packed bytes blob (metacall calldata 24,421 bytes for 41 positions); the implementation then loops, self-calling the proxy with a vanity selector 0xbbbbbbbb and 165 bytes of packed per-position calldata per iteration (market ids, token addresses, borrower, recipient, amounts). One selector; no function per protocol.
- **Funding**: no external flash loan. Per position: Morpho `accrueInterest((MarketParams),...)` (selector 0x151c1ade, 33.9k gas), then Morpho `liquidate((MarketParams),address,uint256,uint256,bytes)` (0xd8eabcb8); Morpho pays out the debt asset from its vault inside `liquidate`, calls the proxy back through `onMorphoLiquidate(uint256,bytes)` (0xcf7ea196), and repays by pulling the debt token from the proxy (`transferFrom` 0x8335 USDC, 9.2k gas). No flash fee observed in the trace (payout + pull only).
- **Exit**: for the sampled batch every position is in the cbUSDC/cbUSDC-style Morpho market (seized asset == debt asset, ledger `fields.seizedAssets`/`repaidAssets` on the same units): no DEX swap per position. The batch converts leftover balance to gas once at the end via `topUpWeth(uint256)` (0xde3fea1f on 0xa7ef..., delegatecall 0x80b5 multicall, internal WETH `withdraw` 0x2e1a7d4d on 0x4200...06). Route fixed inside the contract, not calldata.
- **Profit guard**: per iteration the proxy reads `balanceOf`/`allowance` of USDC (0x8335) and of the collateral token (0xcb58...) plus `previewRedeem` x3 on the Morpho debt token and two Chainlink `latestRoundData` (0x50d25bcd) + `decimals` reads before `liquidate` (14.6k gas each feed call). Guard is balance/preview-based, measured in the debt token; no `tx.gasprice`/`block.basefee` read found inside the guard (the batch tx gas is paid by the Atlas submitter EOA).
- **Cheap miss (measured on the fork)**: the same batch tx re-sent at block 57399504 (positions already seized) ended status 1 with gasUsed 525,090 and zero logs - every iteration self-skips after its preview checks instead of reverting the batch. Miss cost ~525k gas (~10% of the 5,061,760-gas batch) at no revert; farm's executor reverts a full miss at ~its revert gas instead.
- **Priority fee**: txs carry different `maxPriorityFeePerGas` (15 gwei on tx 0xd96c090d..., 148149542 wei on 0xb616a5ad...) - scaled per tx, not fixed; no `block.coinbase` payment in the trace (Atlas fee path is the router callback 0xf68b84f7 + payments to 0x1c6e...).
- **Batching**: yes - up to 41 liquidations in one tx (measured); the per-iteration self-call averaged 88,039 gas (41 self-calls, sum 3,609,612 of the 5,061,760 total; the first iteration cost 198,852). Amortized ~123.5k gas/liquidation including entry and exit.
- **Where profit stays**: the proxy receives the WETH-withdrawn ETH (WETH sends ETH to the proxy, fallback delegatecall 0x43) and forwards it to `0x1c6ec84518b859ae6a96c7dd0c78048be7def976` (plain CALL) - profit leaves the contract as ETH to an operator wallet; nothing is kept in the contract.
- **Gas side-by-side**: farm's executor on the same case: unmeasured (farm has no deployed Base Morpho liquidation executor; the archived morpho-watcher-base path was a watcher, not an executor). d128's numbers above stand alone.

Flaws (fork-only, not sent on mainnet): the packed iteration calldata carries the borrower and recipient - access control of the 0xbbbbbbbb iteration entry (who may self-call) remains unknown from the trace; not audited.
