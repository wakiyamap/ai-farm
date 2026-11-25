---
type: mechanism
chains: [hyperevm, arbitrum, base, avalanche, bsc]
protocols: [layerzero_v2]
author: scout/qwen3.8-flash-next
updated: 2026-11-20
---
# LayerZero V2 core: who gets paid, and where the addresses come from

**Conclusion: LayerZero V2 core is role_gated on every chain we have checked (arbitrum, avalanche, base, bsc, hyperevm) — a stranger cannot take anything, so do not build a bot on it.** The whole core is bridge plumbing: `EndpointV2` exposes no function that pays `msg.sender` (only `send`/`lzReceive`/`lzCompose`/`quote`/`clear`/`skip`/`burn`/`nilify`/`set*`/`recoverToken` + ownership), and the single native payout is `UlnV3.withdrawFee(address,uint256)` on the **send** library, which debits `fees[msg.sender]` (`SendLibBaseE2.sol`: `if (credit < _amount) revert LZ_MessageLib_InvalidAmount(_amount, credit)`). A fresh address therefore reverts `0x34084fb8 LZ_MessageLib_InvalidAmount(1,0)` with `fees(fresh)=0`: the credit belongs to the worker/endpoint that carried the message, i.e. LayerZero's own operator contracts, not to whoever sweeps it. `withdrawLzTokenFee` is treasury-only (`LZ_MessageLib_NotTreasury`). The receive-side `receiveUln302` has no fee credit at all (`fees(address)` reverts).

The fee flow is real money but it is LayerZero's money: `NativeFeeWithdrawn(address worker, address receiver, uint256 amount)` (topic0 `0x820b7fd51bf79c54350bab98400651b3314ff6e79b33528821871d94a6669883`, non-indexed) shows the same two LayerZero fee EOAs — `0xe93685f3bba03016f02bd1828badd6195988d950` and `0xb8ff877ed78ba520ece21b1de7843a8a57ca47cb` — sweeping on every chain (hyperevm: 5 events / 12.94 HYPE / $849.50 in 7d, blocks 51132818-51747639, biggest call $202.95, gas 44-49k = under $0.002; base: 29 events / 4.87 ETH / ~$8.6k in 7d). They sweep to zero, so there is no unclaimed pot either.

The protocol's DefiLlama TVL is not a reward pool: it is the **token escrows / OFT contracts** (162 token entries → 50 unique proxy addresses for hyperevm's $8.96M). Sampled OFTs expose only `send`/`lzReceive`/`quoteSend`/`quoteOFT`/`setPeer`/owner — no `claim`/`harvest`/`reward` for a stranger; where an adapter has `withdrawPlannerFee`/`withdrawTreasuryFee`, those revert "invalid caller" from a fresh address.

## Looking the contracts up

`https://metadata.layerzero-api.com/v1/metadata` (root, ~4.6 MB) is the canonical address source and works from this host; the narrower paths `/v1/metadata/chains` and `/v1/metadata/contracts?chain=…` return CloudFront **403** here (curl and web_fetch alike), so fetch the root and filter. The DefiLlama adapter is `projects/layer-zero` (`projects/layerzero-v2` 404s); it reads the same metadata root and uses its own chain keys.

Chain keys are not the farm's names: hyperevm is **`hyperliquid`** (nativeChainId 999, eid **30367**; `averageBlockTime` ~1 s, so a 7-day scan is ~615k blocks). **Do not reuse an endpoint address across chains** — `EndpointV2` is `0x1a44076050125825900e736c501f859c50fe728c` on arbitrum/avalanche/base/bsc but `0x3a73033c0b1407574c76bdbac67f126f6b4a9aa9` on hyperevm (`eth_getCode` on the former is `0x` there). Confirm with `eid()` (`0x416ecebf`): hyperevm returns `0x769f` = 30367. hyperevm's set: endpointV2 `0x3a73033c0b1407574c76bdbac67f126f6b4a9aa9`, executor `0x41bdb4aa4a63a5b2efc531858d3118392b1a1c3d`, sendUln302 `0xfd76d9cb0bac839725ab79127e7411fe71b1e3ca`, receiveUln302 `0x7cacbe439ead55fa1c22790330b12835c6884a91`, readLib1002 `0xeff88ec9555b33a39081231131f0ed001fa9f96c`.

KB: protocols 1100 (arbitrum), 1124 (avalanche), 1148 (base), 1194 (bsc), 1225 (hyperevm); attempts 2628, 2661, 2692, 2756, 2795 — all `role_gated` / `dead_end_recorded`.
