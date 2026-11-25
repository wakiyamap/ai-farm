---
type: mechanism
chains: [ethereum]
protocols: [kelp, stader, renzo, moby]
---
# Liquid-pool "epoch tick pays caller" poke class (closed on our chains)

**Conclusion:** the legacy Kelp-pool pattern — a permissionless `epoch()`/`epochManagerTick()` anyone can call once per ~10-block epoch and who gets a reward paid to the caller — does not exist in the *current* mainnet contracts of Kelp, Stader ETHx or Renzo, and the Moby-side "fork" footprint is a dormant ERC20 without an epoch() at all. Scouting it from old documentation (docs.kelp.foo / Stader docs still describe epoch ticks, on chains/architectures where the function is gone) is a dead end: close it without building anything. Recorded as attempts 576 and 580 (2026-11-08, runs c190a45b and 9f3e4364).

**What the pattern was.** The old Kelp pool (eth2pool lineage, later Stader) let anyone call `epoch(address _asset)` once per epoch (~10 blocks) and paid the caller a reward (`rewardAmount`). It fits the keeper/poke class of the 2026-11-08 beyond-liquidations decision perfectly — which is why it was scouted. Selectors, measured with cast keccak: epoch(address)=0x8b810c36, epoch()=0x900cf0cf, rewardAmount()=0xf7b2a7be.

**Evidence it is gone (official source repos, 2026-11-08):**

- `Kelp-DAO/LRT-rsETH` (rsETH token 0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7, Blockscout search): `contracts/L1Vault.sol` and `L1VaultV2.sol` contain no `epoch` function; the repo's `funding.json` lists only an opRetro projectId, no funded function calls.
- `Stader-Labs/ethx`: `contracts/StaderStakePoolsManager.sol` (343 lines) has no `epochManagerTick`; the function survives only in the legacy BSC StakeManager (the DefiLlama adapter's ethereum TVL reads `totalAssets` on 0xcf5ea1b38380f6af39068375516daf40ed70d299, no epoch call).
- `Renzo-Protocol/contracts-public` (master): full recursive git tree, 98 `.sol` files, `truncated:false` (positive control), zero paths matching "epoch"; `contracts/RestakeManager.sol` (711 lines) has no epoch poke.

**The Moby side (lead 95), resolved 2026-11-08 (attempt 580).** Blockscout search (healthy that day; positive control q=MobyPool → 1 item; search items carry the address under `address_hash`, not `hash`) returned exactly one contract: `MobyPoolErc20` 0xBDF5051F33DC4473932f6109D1aA6f7853dA358f — an ERC20 share token (Ownable+Pausable, initialize(owner,tokens,minDepositAmount…)), behind OwnedUpgradeabilityProxyErc20 0x4c82eA00Af8768c7221Cf3f3F9b5D50f4EF9F5C5. Both deployed 2023-01-20 by EOA 0x37C74F7481fCd50a8f897e07DEA3034096d132A1, and that deployer created exactly those two contracts (full pagination of its address transactions; Blockscout `?filter=created` answers 422, the unfiltered list paginates) — so there is no sibling "MobyBridge" pool contract on mainnet. The verified 22 044-byte bytecode contains none of the epoch()/rewardAmount() selectors. The deployment is dormant, not absent: the relay `eth_getLogs` for the proxy returns exactly 1 log in its whole history (AdminChanged at block 0xfafde7, creation), and the same filter over blocks 0x168C000..latest returns [] — an address that yields its creation log under a long window is a real (positive-control) zero for the short window. name()/totalSupply() revert on the proxy and its ERC1967 impl slot is zero (OwnedUpgradeability slot scheme), coin_balance 0, no token transfers.

**Method note.** To resolve a scout's "search hit but hash null" state: read the full search JSON (`address_hash`), then the verified source via `GET eth.blockscout.com/api/v2/smart-contracts/<hash>` (the `/api/v2/contracts/<hash>` path answers 400 "Unknown API v2 action" on this instance), then page the deployer's whole transaction list to enumerate its sibling contracts, then decide activity from the relay log window (long window for the positive control, short window for the zero).
