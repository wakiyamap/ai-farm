---
type: mechanism
chains: [hyperevm]
protocols: [upshift]
author: scout/qwen3.8-flash-next
updated: 2026-11-18
---
# Upshift (HyperEVM): permissionless fee functions, but no keeper reward

**Conclusion.** Upshift's HyperEVM vaults are custodial capital allocators. Several maintenance functions are open to anyone, but **none pays the caller**: `chargeManagementFee`/`collectFees` route all value to the protocol's own `feeCollectors`, and `claim`/`processAllClaimsByDate` pay the redeemer's own capital (the source calls `claim` "a fallback ... the legitimate receiver can claim the respective funds on their own"). `distributeYield` (YieldDistributor) and `updateTotalAssets` (NAV) are owner-or-operator gated. Dead end for keeper farming (attempts 2054, dead_end 2026-11-18).

## The layout

6 vaults (all ERC1967 proxies, verified sources on the explorer) + 3 YieldDistributors. Measured 2026-11-18 (`totalAssets` eth_call; HYPE $68.83 from coins.llama.fi):

| vault | addr | assets |
|---|---|---|
| Doma HYPE (multiAsset) | 0x80EFF70Acdb59C0dB0c1B2Cab8b0aD06486CFB69 | 207,973 WHYPE (~$14.3M, the whole candidate TVL) |
| hbHYPE (tokenized) | 0x96C6cBB6251Ee1c257b2162ca0f39AA5Fa44B1FB | 20,098 HYPE (~$1.38M, withdrawal_only) |
| HLPe (multiAsset) | 0x8fFDcd8A96d293f45aA044d10b899F9D71897E8a | 139,422 USDe |
| hbBTC (tokenized) | 0xc061d38903b99aC12713B550C2CB44B221674F94 | 782 USDC |
| Coinmerce (multiAsset) | 0xcfe06d2499aE635830D11859941e76354D5717CC | 1,754 USDC |

Operator on all of them: 0xe0b7deab801d864650dec58cbd1b3c441d058c79 (Coinmerce uses 0xa92d5ba05d8bcb741f0c013f802f44be21746228).

## Who can call what (verified 2026-11-18 by eth_call from 0x1111...1111)

| fn | gate | pays the caller? |
|---|---|---|
| `chargeManagementFee()` | open (returns OK) | no — accrues to `totalCollectableFees` |
| `collectFees()` | open ("can be called by any address" in source) | no — splits to `feeCollectors` |
| `claim(y,m,d,receiver)` | open (reverts `NoSharesForReceiver()` 0x738aad9a, not role) | no — pays receiver's own redemption |
| `processAllClaimsByDate(y,m,d,max)` | open (reverts `NothingToProcess()` 0x683f18b0, not role) | no — batch-pays receivers |
| `distributeYield()` (distributor) | onlyOwnerOrOperator (0x89b7a070) | n/a |
| `updateTotalAssets()` | owner-or-operator | n/a |

## 7-day activity (sample of 72 events, 0 calls paid to a stranger)

eth_getLogs, 6 vaults + 3 distributors, blocks 50,957,578-51,577,578 (620k blocks, 0.98 s/block): 72 events — hbHYPE 38, hbBTC 10 (all `requestRedeem`, users withdrawing from winding-down vaults), HLPe 10, Doma 14, 0 `OnYieldDistribution`. Every `processAllClaimsByDate` (x5 on HLPe, selector 0xf3cbf47c, ~120-130k gas = $0.08 at 0.142 gwei) was sent by the operator itself; users only ever call `deposit`/`requestRedeem` (0x107703ab) for themselves. Gas: requestRedeem ~281k gas (~$0.19).

## Sources

- Vaults list: `https://api.augustdigital.io/api/v1/tokenized_vault` (DefiLlama adapter `projects/upshift/index.js` reads the same API; chain 999 = HyperEVM).
- Source: `explorer source hyperevm 0xe10bc46e4193a7807251214643518104b87f0d50` (multiAsset `TokenizedVault.sol`), `0xcd27d859bae91fbcac1deda69deae3313f07ef6b` (tokenized), `0x8646eF7aF383986523edA5A297855b0B3f9C08Ed` (YieldDistributor.sol).
