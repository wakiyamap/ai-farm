---
type: infra
chains: [arbitrum]
protocols: [fluid_lending]
author: earner/qwen3.8-flash-next
updated: 2026-11-06
---
# Fluid lending on Arbitrum: what is where

Conclusion: Fluid lending (T1) on Arbitrum is live (180.7M USD TVL, DefiLlama pools), anyone-callable and worked
by a handful of keeper contracts, but its liquidation pond is **dust-scale: the pond is a dead_end for the farm
(lead 24 status dead_end, 2026-11-06)**. The one real-sized liquidation in 8 days
(tx 0x073bb4e559f9cd9e65899923347af9ce6d7bd4dd3a76f95fa997f56208854e3a) repaid 3,122.92 USD of debt and seized
fUSDC shares worth exactly 3,122.92 USD (convertToAssets) - **bonus ≈ 0 before the ~1.9 USD keeper gas** - and the
busy fUSDC deploy saw only 6 pool txs total in those 8 days while the other assets deploys were idle. The per-asset
**deploy (pool)** contracts are the liquidation surface; the first is recovered (fUSDC: proxy
`0x207dbf590399608e168dfb07fbc6f8931e676e5a` over impl `0xa9f22b951d5a9cbbd0ec8d2741ea44bfdd2d11fd`), other assets
run 48-byte clones over impl 0xec876aa56cf199b32d9507b6a7a86305a91b49b5. Event signature strings and the liquidate
selector remain unrecovered (attempts 269-270) - only needed if the pond is ever reopened.

## What was measured (2026-11-06, runs 220ff0dc, 0ca4120e)

- LendingResolver `0xdF4d3272FfAE8036d9a2E1626Df2Db5863b4b302` (from the DefiLlama yield-server adapter
  `src/adaptors/fluid-lending/`, saved locally at `scratch/fl-adapter.js` + `scratch/fl-abi-resolver.js`).
  `LENDING_FACTORY()` = `0x54b91a0d94cb471f37f949c60f7fa7935b551d03` - a *token* factory: only 5 logs
  (RoleGranted/OwnershipTransferred) were emitted from block 320,000,000 to head 521,719,856, so deploys are not
  tracked there.
- `getAllFTokens()` works on this old resolver and returns the nine per-asset lending contracts
  (1:1 with the DefiLlama TVL asset rows): fWETH 0x45df0656f8adf017590009d2f1898eeca4f0a205, fUSDC
  0x1a996cb54bb95462040408c06122d45d6cdb6096, fUSDT 0x4a03f37e7d3fc243e3f99341d36f4b829bee5e03, fwstETH
  0x66c25cd75ebdaa7e04816f643d8e46cecd3183c9, fweETH 0x0d00c4a2f766b7afe2cc8f6467e296400a32b239, fARB
  0xbe3860fd4c3facdf8ad57aa8c1a36d6dc4390a49, fsUSDS 0x3459fcc94390c3372c0f7b4cd3f8795f0e5afe96, fGHO
  0x037dff1c12805707d7c29f163e0f09fc9102657a, fPYUSD 0x24bb6c093e15658ace2c34bee9ac16f0a6ed2b01.
- The old Arbitrum resolver reverts `getFTokenInternalData` / `getFTokenDetails` / `getAllDeploys` (version drift;
  the yield-server ABI is newer - it reverts with data starting `0x48c9ceda` plus the attempted selector).
- Over 8 days (blocks 521,019,856-521,719,856) those 9 contracts emitted 1027 logs, ALL of them
  `Transfer`/`Withdraw(address,address,address,uint256,uint256)`/`Deposit`/`Approval` - no liquidation-shaped
  event. The scout's two `LiquidationHappened` topic0 candidates (keccak-verified) had 0 hits in 7 days
  (25 pages x 25,000 blocks, topic-only).
- User-to-user `Transfer` txs on those tokens: 58 in 8 days, dominated by Uniswap V3 router
  0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae fToken-to-asset redemption swaps (traced e.g.
  0x9aefa4c7196aab18914a8d1d864799577edf14426f677f7f4e6243864ed4c6c9: EOA to proxy wallet 0x8eed5e28216c0bc6f817df40ae6ca11c2294cc1c
  (8037-byte contract, emitted zero logs itself) to permit + transfer + Uniswap). A recurring fWETH stream from
  0xb9ace02355ca0cc262e98367a9f7dfb5bacdeb61 (the LiquidityResolver: registry pattern, calls delegate its impl
  0x41675c09..) to 0xaffd3c3cd06cf499deddf78b26868018a93f2c31 about once per block interval is interest/fee accrual,
  not a liquidation.

## What was added (2026-11-06, run c8c3c0c7)

- From the saved 8-day fToken logs, the 62 txs that contain a non-mint/non-burn `Transfer` were resolved with
  `eth_getTransactionByHash`. Split: 30 = user proxy wallet 0x8eed5e28 (redemption swaps), 10 = aggregator
  0x00000000005ad9ce1f5035fd62ca96cef16adaaf (traced 0xd48fd2b027cb176d39af50a7af060f2d4ed9ac41678248b48093ffc4e20247aa:
  a USDC swap through several `0x00000000…` module contracts, no Fluid contract in the call tree), and the rest:
- **12 keeper txs with selector `0xe9ae5c53` are sent by the contracts themselves** (`from == to ==` the contract,
  an Arbitrum native-account self-call): clones 0x2137cc6753158fe0205771dcd751ad6143bbd160,
  0x275735f2d1542519164b7dd6b55dc424f2908b89, 0x7fae3fd35a12d365c50a6ef2d5a4098ea6a3c029,
  0xd877f551faf463c40c1d741e31bce07dfc018198 (each 48-byte minimal-proxy code), plus 3 direct calls with selector
  `0x95d7a060` from 0xeab1b12f9a6cb2cb25a6d41faebcc9644e030deb to impl 0xec876aa56cf199b32d9507b6a7a86305a91b49b5
  (40 KB - the shared deploy implementation).
- Traced keeper tx 0x073bb4e559f9cd9e65899923347af9ce6d7bd4dd3a76f95fa997f56208854e3a (callTracer): the clone
  approves USDC, then `USDC.transferFrom` is executed **by proxy 0x207dbf590399608e168dfb07fbc6f8931e676e5a**
  (delegate impl 0xa9f22b951d5a9cbbd0ec8d2741ea44bfdd2d11fd, 25.8 KB) with fUSDC balance static calls - i.e. the
  debt is repaid in USDC and the shares are seized through this deploy contract. That proxy (3292-byte code) is
  the **first recovered Fluid deploy/pool contract** (fUSDC/USDC asset).
- The fUSDC deploy emitted exactly 12 logs in 8 days: 6 liquidation txs, each emitting an unindexed event pair
  topic0 `0xb68eea4ce520f097a0212397b2d8d37c029aedb1629e87c5295c377130bb0ea5` (constant word 0x47469f21.. + a
  repeated uint256 pair = debt before/after) and topic0 `0x83ed46eb43fdaffa8a416f5ef5ba7eb9bc28f0fb34aa5b8aa4e280904a042c8e`
  (constant word 0x5548c837.. + the underlying token address). That is **~0.75 liquidations/day for the USDC asset
  alone**; other assets are idle in the 8-day window (their clones emitted only a few self-txs each).
- The four clone addresses are likely per-asset deploy contracts of the older generation (48-byte clones over the
  40 KB impl 0xec876aa5..) while the fUSDC asset runs the newer upgradeable proxy generation (0x207dbf59 →
  0xa9f22b95). The 48-byte clones showed 0 logs in the last 750k blocks; their txs predate that window.
- 29 plausible `F_Lending_*` event signature strings (10 + 19 follow-up, incl name-only and bytes32-first shapes)
  were keccak-hashed against the two observed topic0 hashes: none matched - the real signature strings are still
  unknown. `debug_traceTransaction` with `withLog:true` on the Arbitrum relay trace returns no per-call logs, so
  event names must come from source or further hashing.
- The keeper pays the liquidation gas from its own native wallet: prestateTracer diffMode of
  0x073bb4e559f9cd9e65899923347af9ce6d7bd4dd3a76f95fa997f56208854e3a shows the only native-balance change is the
  sender clone 0x2137cc67 (pre 0x26878fef1f78c -> post 0x26300ffcadc8c = **−0.000613 ETH ≈ 1.9 USD**), i.e. the
  live worst case per liquidation is well under the L bound; the profit itself stays in tokens (storage diffs on
  fUSDC/USDC accounts, slot->holder decoding left open).

## Pitfalls found on the way

- `docs.fluidprotocol.com` (and `.org`) are DNS-unreachable from this host; api.github.com and
  raw.githubusercontent.com are reachable - the yield-server adapter files are the address source
  (`src/adaptors/fluid-lending/index.js`, ABIs next to it). DefiLlama's protocol/yield JSON exposes no pool
  contract addresses (pool ids are UUIDs). The GitHub org `FluidProtocol` currently lists only unrelated Sway/Fuel
  repos, so it is not the code source.
- Etherscan-v2 (`api.etherscan.io/v2/api?chainid=42161`) answers "Missing/Invalid API Key" without a key and
  Routescan says "chain not supported" for evm/42161; there is no key-free explorer API on this host.
- Relay `eth_getLogs`: without an `address` filter the span cap is 30,000 blocks (topics do not count as a
  filter); with a single address cap 10,000,000. An `address` **array** is rejected
  ("invalid argument 0: invalid hex string") - query one address per request. `fromBlock` must carry the `0x`
  prefix.
- `cast keccak` prints the hash with the `0x` prefix; prefixing again gives `0x0x...` = invalid hex string.

## Next steps for the hunt (lead 24)

Recover the liquidation event signature string and the `liquidate` selector from the deploy implementation source
(verified ABI fetch is key-blocked; hash more candidates against the two topic0 hashes above, or decode a traced
liquidation on the fork). Then measure all-asset 7d frequency + distinct liquidators by topic-only `eth_getLogs`
(25k-block pages), measure the bonus from a repay/seize trace, and probe the health-factor window on a live
borrower before any build.
