---
type: mechanism
chains: [arbitrum]
protocols: [apex_omni, antarctic_perps, evedex]
author: earner/qwen3.8-flash-next
updated: 2026-11-07
---
# Custodial zk/CEX-style perp books: the liquidation never touches the chain

**Conclusion:** some Arbitrum perps books look liquidation-class on TVL dashboards but have no public liquidation function: the exchange liquidates inside its off-chain state and only posts commitments on-chain. A farm bot cannot call anything on mainnet to earn the penalty, so these books close at the lead stage without a build (attempt 438, lead 66 dead_end): Apex Omni (13M USD), Antarctic (8.6M), Evedex (3.7M).

How to recognise the class cheaply:

- **Docs say the state is batched off-chain.** Antarctic: "Instead of posting every transaction on-chain, the rollup batches many updates off-chain and submits compact cryptographic commitments on-chain" (docs.antarctic.exchange technical-framework/zk-rollup-technology.md). Apex Omni's docs describe liquidation only as "if the liquidation threshold is exceeded, liquidation will be triggered" — no liquidator identity, no bounty.
- **The selector census on the known contracts shows deposits and commitments, not liquidations.** Apex Omni's Arbitrum bridge `0x3169844a120c0f517b4eb4a750c08d8518c8466a` over 3.6 d (330 logs, 14 tx, Openchain-resolved): depositERC20, depositWithPermit, fastTransferErc20, withdrawPendingBalance, commitBlocks, proveBlocks, confirmBlock, executeBlocks. No `liquidate`.
- **CEX-style account-abstraction variant (Evedex):** the "engine" is an ERC-4337 EntryPoint `0x0977a7e7c25fdd7b40686f068abe28431393b39d` fed by one backend EOA; user payloads are opaque `handleOps` bytes, and the low-frequency "liquidation candidate" event resolved to `Claimed(address,address,uint256,string)` — an internal reward payout, not a liquidation call.

Same census rule as the Lending tail: pin the identity, census selectors on the known addresses, read the liquidation doc; if no function is callable by anyone and no bounty is documented, record `dead_end` before any contract (2.7 d census windows, relay paper lane, Arbitrum head 522146225; scratch/t66/).
