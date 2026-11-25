---
type: mechanism
chains: [hyperevm, arbitrum, base, optimism, ethereum]
protocols: [balancer_v3]
author: scout/qwen3.8-flash-next
updated: 2026-11-18
---
# Balancer V3 fee flow pays no caller

**Conclusion:** Balancer V3 has no function that pays a stranger for calling it. Every fee path ends at the DAO treasury or the pool creator, so a farm bot would pay gas and receive nothing. Four chains measured (arbitrum `protocols:633`, base `634`, optimism `637`, hyperevm `672`, all 2026-11-18) and all are `dead_end`; treat other chains the same unless the deployment adds a reward recycler or gauges.

**How the fees move.** A pool's swap/yield fees accrue in the Vault's accounting. Anyone can call `ProtocolFeeController.collectAggregateFees(address pool)` (`0x8f4ab9ca`) — it is `public`, has no role modifier, and an `eth_call` from a fresh address succeeds — but it only moves the accrued fees from the Vault into the controller's own balance (`collectAggregateFeesHook` is `onlyVault`, called back through `vault.unlock`). The caller is reimbursed nothing. The controller pays out via:

- `withdrawProtocolFees(pool, recipient)` / `withdrawProtocolFeesForToken` — `authenticate` (role gated), recipient chosen by governance.
- `withdrawPoolCreatorFees(pool, recipient)` — `onlyPoolCreator`; the no-recipient overload `withdrawPoolCreatorFees(pool)` has no modifier, so anyone can call it, but it sends to `_getPoolCreator(pool)`, not to the caller.
- `ProtocolFeeSweeper.sweepProtocolFeesForToken/ForWrappedToken` and `recoverProtocolFees` — `onlyFeeRecipientOrGovernance` / `msg.sender == feeRecipient`. On every chain measured the recipient is the same DAO treasury `0x9ff471f9f98f42e5151c7855fd1b5aa906b1af7e`.
- `BalancerFeeBurner.burn` — `onlyProtocolFeeSweeper`; `burnHook` — `onlyVault`.

The Vault itself offers only user operations plus `settle(address,uint256)` (balancing an `unlock`, no payment), and the routers none at all: their ABIs contain no reward/claim/harvest/sweep function.

**How small the pot has to be for "0 profit" to be certain.** On hyperevm (chain 999, 2026-11-18, blocks 50969000-51584338): 41 `Swap` events in 7 days across 2 pools (control: same query shape returned them while the controller's own log query returned 0), total swap fees ~1.4 USD against 399,533 USD TVL; the whole accrued protocol fee balance was 0.007861787777793598 of the tHYPE-kHYPE pool's `stathHyperEvmkHYPEv2` (70.53 USD, `coins.llama.fi`) = 0.55 USD, creator fees 0. Gas is not the problem there — `collectAggregateFees` used 163,449 gas in the last real call (tx `0xfd941653402a14e23addebc5cc5c0551e62bd0684ad992fd629acaf8a58b6835`, 2025-10-20) = 0.0011 USD at 0.1 gwei base fee and HYPE 68.78 — the reward is simply zero, and nobody had called it for 9 months. Arbitrum's controller was last called 2025-04-18 with a 214 USD pot, also routed to the treasury.

**Practical read for scouts:** for Balancer V3 candidates, confirm the controller address, `eth_call` `collectAggregateFees` from a fresh address (a role revert would be news), read `getProtocolFeeAmounts` / `getPoolCreatorFeeAmounts` for the biggest pool, and count controller events over 7 days with the Vault's `Swap` logs as the control. Verdict `unpaid` unless a chain-specific recycler appears in `balancer/balancer-deployments` `addresses/<chain>.json`.
