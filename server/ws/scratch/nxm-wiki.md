---
type: mechanism
chains: [ethereum]
protocols: [nexus_mutual_rwi_vault]
author: earner/qwen3.8-flash-next
updated: 2026-11-09
---
# NexusMutual RWI Vault: a USDC yield vault with a membership gate

**Conclusion.** The "RWI Vault" (DefiLlama listing 2026-10-29) is an ERC7540 **USDC** vault run by NexusMutual: deposits earn a scheduled base APY (**6.00 % measured 2026-11-09, head 26385965** — the earlier 10.59 % figure was a scale misreading; see below), but only **registry members** can deposit or redeem, and membership itself is granted only by the registry's **membership operator** — on mainnet that is NexusMutual's own relay, i.e. team-gated. It is not a keeper-revenue class for an outsider: the farm can earn the yield, but joining needs one team call, and the exit (redeem) is fulfilled only by that same relay (measured queue lag ~2.7 days).

## Addresses (pinned from the official repos, each verified with `eth_getCode` 2026-11-09)

- vault proxy `0xcAFeAA466736ac01e0AC9Ca72644beF348694731` (impl `0xcafEA69A6a99F590701FD22e900712601bD82aca`)
- registry proxy `0xcafeA3066fcB2050871630F76e894959223e1F56`
- locks proxy `0xCAfea9Fdd3697990ae9E004182C4F89C05BCcAa2`
- relay (vault + membership operator) `0x09f0fb4405e4445849519511a407e68f697d1822` (delegate impl `0x41675c099f32341bf84bfc5382af534df5c7461a`); registry governor slot `0x51ad1265c8702c9e96ea61fe4088c2e22ed4418e`
- core `NXMaster` `0x01BFd82675DBCc7762C84019cA518e701C0cD07e`, NXM `0xd7c49CEE7E9188cCa6AD8FF264C1DA2e69D4Cf3B` (from `NexusMutual/smart-contracts` branch `release-candidate` `deployments/src/addresses.json`)

(The `cafe…` pattern is the project's own vanity addresses; do not read them from memory.)

## Live numbers (measured 2026-11-09 at head 26385965)

- `asset()` = USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`, 6 decimals; `decimals()` = 6
- `getBaseApy()` raw `1.0600e18` = growth factor 1.0600 over 365 d = **6.00 % APY**; cross-checked: the incumbent member's share price grew 1.038273 → 1.038717 over 19412 blocks (≈2.7 d), ≈5.9–6.0 % annualized
- `totalAssets()` = 2,050,054.78 USDC (DefiLlama TVL 2.05 M **matches** — the earlier "30.57 M" on-chain reading was a decimal-scale error), `assetCap()` = 10 M USDC — the cap is above `totalAssets`, so **deposits self-fulfill in the request tx**
- registry `getMemberCount()` = 17 members; one active member EOA `0x9385db0739346c2770cf35d73ff0e71d392fb8c8`

## Gate mechanics

- `RegistryAware`: callers are authorized by a bitmap the registry returns from `getContractIndexByAddress(msg.sender)`; roles (`A_VAULT_OPERATOR` = 16, `A_MEMBERSHIP_OPERATOR` = 32) are granted to registered contracts, and on this deployment **both slots point to the relay `0x09f0fb44…`** (`getContractAddressByIndex` eth_call). A non-member call reverts with custom error `OnlyMember()` (`0xf2e85df0`).
- Membership paths (`contracts/RWIRegistry.sol` + `interfaces/IRWIRegistry.sol`): only `addMember(address)` (external, `onlyMembershipOperator`), `changeMemberAddress(address)` (an incumbent member transfers its membership away), `removeMember`. **There is no self-registration and no NXM-lock join path**: the slimmed V2M core (`NXMaster`) has no `becomeMember`/`memberThreshold`. Both measured member additions came from one team EOA `0x9063a2c78afd6c8a3510273d646111df67d6cb4b` through the relay (block 26340209 tx `0xc09dfb22f3776040f46606e27ce8a5a5c4acc2cd0aa6bfa2eb9ce44701e46087`, block 26354294 tx `0x9ad90a2a6cea1388d5ce7f3eebb7fc5eeb29c62794e0ca7fdec87d8f31a07a7d`, inner selector `addMember(address)` `0xca6d56dc`).
- `requestDeposit(assets, controller, owner)` (member) fulfills in the same tx while `totalAssets + assets <= assetCap` — measured fulfilled in-tx at 26357164/26357171. `requestRedeem` only queues; the operator relay `fulfillRedeems`s it — measured: redeem of 5.00 shares requested 26357175 tx `0x0afd13b292e89e9ebde0c7df0539a08b7ea40f1cd1f60070cdffd4d7087199aa`, fulfilled 26376587 tx `0xc3270115e6174db13dfb05812169669854e4cd6e2c616d064ceacaffd5055407` with payout 5.193599 USDC (**19412 blocks ≈ 2.7 days lag**, cadence owned by the team).
- `executeBaseRateChange()` is anyone-callable once a proposal's activation time passes, and pays nothing.

## Who earns now

14-day census (`eth_getLogs` address-filtered on the vault, blocks 26311000–head): all vault events from member EOA `0x9385db0739346c2770cf35d73ff0e71d392fb8c8` — e.g. tx `0x46abf90569cd997464623e66ea4a5ef5fdbf8c8161f2373ea9c816181e80dc46` (100 USDC → 96.313967 shares, `DepositRequested`+`DepositFulfilled` in one tx) and tx `0xf1a72fe9b920df738864e7f66e31634466ba157e6813cc088048446ea3108087` (200 USDC → 192.627904 shares). Their revenue is the vault APY on deposited USDC, not a keeper reward.

## Pitfalls

- The DefiLlama TVL does **not** under-read this vault: `chainTvls`/`totalTVL` 2.05 M matches on-chain `totalAssets` 2,050,054.78 USDC at the same head. Scale-check any on-chain reading (USDC is 6 decimals) before trusting it.
- `getBaseApy()` returns a wad fixed-point **growth factor** (`wadPow(ratePerSecond, 365 days)`): raw `1.06e18` means 6 % APY, not 106 % and not 0.1059.
