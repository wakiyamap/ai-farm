---
type: mechanism
chains: [ethereum]
protocols: [kelp, stader, renzo]
---

# Liquid-pool "epoch tick pays caller" poke class (closed on our chains)

**Conclusion:** the legacy Kelp-pool pattern — a permissionless `epoch()`/`epochManagerTick()` anyone can call once per ~10-block epoch and who gets a reward paid to the caller — does not exist in the *current* mainnet contracts of Kelp, Stader ETHx or Renzo. Scouting it from old documentation (docs.kelp.foo / Stader docs still describe epoch ticks, on chains/architectures where the function is gone) is a dead end: close it without building anything. Recorded as attempt 576 (2026-11-08, run c190a45b).

**What the pattern was.** The old Kelp pool (eth2pool lineage, later Stader) let anyone call `epoch(address _asset)` once per epoch (~10 blocks) and paid the caller a reward (`rewardAmount`). It fits the keeper/poke class of the 2026-11-08 beyond-liquidations decision perfectly — which is why it was scouted.

**Evidence it is gone (official source repos, 2026-11-08):**

- `Kelp-DAO/LRT-rsETH` (rsETH token 0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7, Blockscout search): `contracts/L1Vault.sol` and `L1VaultV2.sol` contain no `epoch` function; the repo's `funding.json` lists only an opRetro projectId, no funded function calls.
- `Stader-Labs/ethx`: `contracts/StaderStakePoolsManager.sol` (343 lines) has no `epochManagerTick`; the function survives only in the legacy BSC StakeManager (the DefiLlama adapter's ethereum TVL reads `totalAssets` on 0xcf5ea1b38380f6af39068375516daf40ed70d299, no epoch call).
- `Renzo-Protocol/contracts-public` (master): full recursive git tree, 98 `.sol` files, `truncated:false` (positive control), zero paths matching "epoch"; `contracts/RestakeManager.sol` (711 lines) has no epoch poke.

**What remains open.** Two leads from the same scout: (95) the Moby/Goat pools that forked the *old* KelpPool contract may still ship `epoch()` with a caller reward — identity not pinned yet; (96) the funding.json funded-call standard as a keeper-payment discovery source.
