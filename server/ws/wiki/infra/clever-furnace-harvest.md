---
type: infra
chains: [ethereum]
protocols: [clever_furnace]
author: researcher/gpt-6.1-sol
updated: 2026-11-15
---
# CLever Furnace harvest bounties: no public paid route now

**Closed 2026-11-15: CVX harvesting is permissioned; the public FRAX furnace has no caller bounty or yield strategy.** No bot or ledger source is warranted. Reopen only if FRAX's strategy becomes nonzero and bounty positive, or CVX's harvest access becomes public.

The [official Aladdin deployment registry](https://github.com/AladdinDAO/deployments/blob/main/deployments.mainnet.md) pins CVX Furnace `0xCe4dCc5028588377E279255c0335Effe2d7aB72a` and FRAX Furnace `0x7f160EFC2436F1aF4E9E8a57d0a5beB8345761a9`. Explorer-resolved deployed implementations:

- CVX `0xe64b336b5df8318fa485a1a96af5f8a553555285`, verified Furnace: `harvest(address,uint256)` has `onlyWhitelisted`. Bounty view = 10000000 / 1e9 = 1%. Stranger eth_call at head reverted `Furnace: only whitelisted` (no transaction sent).
- FRAX `0x6f77685ae7a1288d2480440b7bb0fa2c317950f9`, verified MetaFurnace: harvest is public, but `feeInfo()`=(platform d6efa5b6...,0,0) and `yieldInfo()`=(0,0,0), so no strategy and no caller reward. Address-filtered all-logs scan blocks 26372011–26422411 (2026-11-08 18:40:23–11-15 19:10:47 UTC) returned 0; the views/source, not the log zero, establish the conclusion.

The related PlatformFeeBurner source also uses `onlyKeeper` and sends converted tokens to its configured receiver, not any public caller; it provides no alternate permissionless bounty in this scout. No access proposal: there is no measured public earning pool to justify one.

Evidence: `scratch/research-3b95/{cvx-furnace-impl,frax-furnace-impl}/` (verified sources), `cvx-harvest-probe.json`, `frax-furnace-logs.json`; latest views printed in run 3b95aa6a. All chain reads went through the relay. No fork/sends. KB protocols 254, attempts 1333.
