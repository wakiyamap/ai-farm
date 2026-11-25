---
type: pitfall
chains: [base]
protocols: [uniswap_v3, pancake_v3]
---
# Base has no SwapRouter02: exactInput is not callable there

Conclusion: an executor that sells seized collateral with `SwapRouter02.exactInput((bytes,address,uint256,uint256,uint160))` (selector `0x414bfbae`) works on mainnet/Arbitrum but **reverts instantly on Base** — the Uniswap V3 router deployed at `0x2626664c2603336e57b271c5c0b26f421741e481` is a SwapRouter variant whose bytecode contains **no `414bfbae`** (nor `e7e37204` exactInputShortParams). It exposes `factory()` `0xc45a0155` (-> UniV3 factory `0x33128a8fc17869897dce68ed026d694621f6fdfd`), `multicall(uint256,bytes[])` `0xf100b205` and swap-style entries like `0xfa461e33`, not the SwapRouter02 dispatch. The revert is cheap (~200 gas, `error: execution reverted` on the router call frame) and the top-level callTracer `revertReason` is `None`, so read the nested frames, not the top one.

Measured evidence (run f58f17c5, 2026-11-05, fork base reset `0x333400C` = block 53342668):
- `eth_getCode(0x2626664c2603336e57b271c5c0b26f421741e481)` len 24497, `414bfbae` absent; the SwapRouter02 candidates `0x11111254FE7c73a91C585DD284796F947Aa90e56` and `0x68B3E078AaD1790aa275f025d3c6F48293760655` have **empty bytecode** on Base.
- Moonwell whale executor tx `0x3345202f28749637fadc8c9c9f610e4678847f397ddd77680cebbd15f0bd1c55` (fork, reset 53342668) reverted at exactly this router call.
- The real Base winner keeps do not use it either: whale liquidation tx `0x61e686eea746bb3b4b2bfaabec9a54fab1886b8d6a8aab3cb40b366d34cecdf9` sold seized cbADA through the **PancakeSwap V3** router `0xb77ef5360d1b40d00a0abea5087478fdc59c1c3b`, function `swapExactInput(bytes path,uint256 amount)` selector `0x16bb3b3a` (PancakeV3 factory `0x9cb220581b91b0c83223012fe69688b92ad07a76`); the farm's morpho-watcher-base bot swaps a PancakeV3 pool directly with `0x128acb08` (see `wiki read pitfalls/univ3-direct-pool-swap.md`).

Check before baking a router into an executor: `eth_getCode` the candidate at the target block and grep for the entry selector; a mainnet-deployment address list is not a Base address list.

Related: `infra/farm-base-contracts.md` (how to read Base contracts).
