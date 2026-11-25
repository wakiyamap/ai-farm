---
type: mechanism
chains: [ethereum]
protocols: [nexus_mutual_rwi_vault]
---
# NexusMutual RWI Vault: a USDC yield vault with a membership gate

**Conclusion.** The "RWI Vault" (DefiLlama listing 2026-10-29) is an ERC7540 **USDC** vault run by NexusMutual: deposits earn a scheduled base APY (10.59 % measured 2026-11-09), but only **registry members** (self-service, `msg.sender` must be member + controller + owner) can deposit or redeem, and redemption is **async**: only the registry-granted `A_VAULT_OPERATOR` contract fulfills redeem batches. It is not a keeper-revenue class for an outsider — the farm can earn the yield, but only after joining the membership gate.

## Addresses (pinned from the official `NexusMutual/rwi-vault` repo `ignition/deployments/mainnet-1/deployed_addresses.json`, each verified with `eth_getCode` 2026-11-09)

- vault proxy `0xcAFeAA466736ac01e0AC9Ca72644beF348694731` (impl `0xcafEA69A6a99F590701FD22e900712601bD82aca`)
- registry proxy `0xcafeA3066fcB2050871630F76e894959223e1F56`
- locks proxy `0xCAfea9Fdd3697990ae9E004182C4F89C05BCcAa2`

(The `cafe…` pattern is the project's own vanity addresses; do not read them from memory.)

## Live numbers (measured 2026-11-09 at head 26377427)

- `asset()` = USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`, 6 decimals; `decimals()` = 6
- `getBaseApy()` = 0.1059… (10.59 % APY, rate accrues per second from `rateConfig`)
- `totalAssets()` = 30.57 M USDC, `totalSupply()` = 19.81 M shares (rate ≈ 1.54)
- `assetCap()` = 10 M USDC — below `totalAssets`, so **new deposits do not self-fulfill**: the queue drains only when the operator calls `fulfillDeposit`
- registry `getMemberCount()` = 17 members

## Gate mechanics

- `RegistryAware`: callers are authorized by a bitmap the registry returns from `getContractIndexByAddress(msg.sender)`; roles (`A_VAULT_OPERATOR` = 16, `A_MEMBERSHIP_OPERATOR` = 32) are granted to **registered contracts**, not EOAs, and only the governor registers contracts. `getContractAddressByIndex(16)` on the registry reverts `ContractDoesNotExist` — the operator slot has no primary address; the NexusMutual core services the queues.
- Member self-service: `requestDeposit(uint256,address,address)` selector `0x85b77f45`, `requestDepositAndLock(…,uint256)` `0x297b9783`, `requestRedeem` `0x7d41c86e`. A non-member call reverts with custom error `OnlyMember()` (`0xf2e85df0`, eth_call measured from a random EOA).
- `requestDeposit` transfers USDC in and **fulfills in the same tx only while `totalAssets()+assets <= assetCap`**; `requestRedeem` only queues — payout comes from `fulfillRedeems(maxRequestId, maxTotalAssets)` (operator role, can partially fulfill).
- `executeBaseRateChange()` is anyone-callable once a proposal's activation time passes, and pays nothing.

## Who earns now

14-day census (`eth_getLogs` address-filtered on the vault, blocks 25984416–26377427): 20 logs / 7 txs — **all from member EOA `0x9385db0739346c2770cf35d73ff0e71d392fb8c8`** (e.g. `0x46abf90569cd997464623e66ea4a5ef5fdbf8c8161f2373ea9c816181e80dc46` emits `DepositRequest` + `DepositFulfilled` in one tx, plus `requestDepositAndLock`, `requestRedeem`, `approve`). Their revenue is the vault APY on deposited USDC, not a keeper reward.

## Pitfall: the DefiLlama TVL under-reads the vault

`api.llama.fi/protocol/nexus-mutual-rwi-vault` shows TVL 2.05 M USD while on-chain `totalAssets` is 30.57 M USDC (measured same day); `chainContracts` is null (renamed-project quirk). Use on-chain getters, not the llama registry, for this protocol.
