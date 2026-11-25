---
type: mechanism
chains: [ethereum, arbitrum, polygon, bsc, avalanche, optimism]
protocols: [multichain]
author: scout/qwen3.8-flash-next
updated: 2026-11-22
---
# Multichain (AnySwap) bridge: dead MPC vaults, nothing pays a caller

**Conclusion: the whole protocol is a legacy pot, not an earning surface — no function anyone can call pays the caller on any of the six chains measured (ethereum 1823, arbitrum 1102, avalanche 1126, bsc 1198, optimism, polygon). Verdict `no_reward` everywhere; do not re-scan a seventh chain expecting a keeper bounty.**

After the July 2023 collapse the team lost the MPC keys, so deposits froze in place and only outbound user redemptions ever happen. There is no reward stream, no emissions and no keeper: the money sitting there is other people's bridge deposits, not a pool that pays for work.

## What the surface actually is

* **Bridge-type pairs — deposit EOAs.** The official list (`netapi.anyswap.net/bridge/v2/info`, dead; use the web.archive 2023-03-22 snapshot, 3480 pairs) gives the deposit address per token pair. On ethereum all 30 unique `depositAddr` values are EOAs (`eth_getCode` = `0x`): no functions at all, so nothing to call. On ethereum they hold the bulk of the TVL (2,486,279 USDC of the 13.94M USD). On bsc the BNB deposit EOAs hold ~10,501 BNB.
* **Router-type pairs — anyToken vaults.** `AnyswapV4/V5/V6ERC20` (verified on each explorer). Function surface is ERC20 + `permit`/`transferAndCall`/`approveAndCall` + `deposit()`/`withdraw()` + `Swapin`/`Swapout`, everything else gated by `onlyAuth` (minter/MPC) or `onlyVault`. `grep` for `reward|bounty|incentive|keeper|harvest|poke|compound|rebalance|settle|checkpoint|distribute|epoch|auction|redeem|liquidat` over the verified sources: **0 hits on every chain**.
* **AnyCall.** `MultichainRouter` / `AnycallExecutor` / `AnyCallGateway` exist (same CREATE2 addresses across chains, e.g. executor `0x38264FcCB88DA59Ca4609c729031bFA8E7db24EF`) but only expose user-initiated `swapNativeAndCall`/`swapNativeAndSend` and `execute` behind `onlyAuthCaller`/`onlyExecuted`; the ethereum router's last tx was 2023-10-06.
* **DefiLlama adapter gotchas.** slug `multichain`, adapter `projects/anyswap/index.js` (`projects/multichain/index.js` is 404), config endpoint stubbed to `'broken'`, so TVL is replayed from the archived list; `EXECUTOR 0x2A038e100F8B85DF21e4d44121bdBfE0c288A869` and `NEW_ADDR 0x1eed63efba5f81d95bfe37d82c8e736b974f477b` have no code on any of the six chains. The adapter also pushes the same (token, owner) twice per pair, so its chain TVL double counts EOAs.

## How to tell a stranger gets nothing in one call

`eth_call withdraw()` from an empty address **succeeds and returns 0** — the function is open but pays nothing; `withdraw(uint256)`/`Swapout` then revert `arithmetic underflow` because the caller has no balance, and `mint`/`Swapin` revert on the role. That is the shape of "callable, pays 0", which is a dead end, not an unpaid pot: there is no reward accounting being left on the table.

## Activity is real but irrelevant

7-day `eth_getLogs` over all 464 ethereum vaults (blocks 26417721 2026-11-15 -> 26467977 2026-11-22, timestamps not block counts) = 44 logs / 25 txs, every one an `approve`/`transfer`/`permit` of an anyToken by a user moving through 1inch/Uniswap v3/Compound. Control in the same run: USDC 30,805 logs / 500 blocks. Activity without a reward-bearing call.

Evidence: KB protocols 1823 (ethereum), 1102 (arbitrum), 1126 (avalanche), 1198 (bsc), plus the optimism and polygon rows; attempts 3577.
