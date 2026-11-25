---
type: infra
chains: [arbitrum]
protocols: [fluid_lending]
---

# Fluid lending on Arbitrum: what is where

Conclusion: Fluid lending (T1) on Arbitrum is live (180.7M USD TVL, DefiLlama pools) and anyone-callable liquidations
must be hunted at the per-deployer **deploy (pool)** contracts, which are NOT the nine per-asset fToken contracts the
resolver lists. Nothing liquidation-shaped is visible on Arbitrum without those deploy addresses, and nobody has
recovered them yet (lead 24).

## What was measured (2026-11-06, runs 220ff0dc and 0ca4120e)

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

## Pitfalls found on the way

- `docs.fluidprotocol.com` (and `.org`) are DNS-unreachable from this host; api.github.com and
  raw.githubusercontent.com are reachable - the yield-server adapter files are the address source
  (`src/adaptors/fluid-lending/index.js`, ABIs next to it). DefiLlama's protocol/yield JSON exposes no pool
  contract addresses (pool ids are UUIDs).
- Relay `eth_getLogs`: without an `address` filter the span cap is 30,000 blocks (topics do not count as a
  filter); with a single address cap 10,000,000. An `address` **array** is rejected
  ("invalid argument 0: invalid hex string") - query one address per request.
- `cast keccak` prints the hash with the `0x` prefix; prefixing again gives `0x0x...` = invalid hex string.

## Next steps for the hunt (lead 24)

Recover the deploy (pool) contracts: trace the non-router transfer txs in `scratch/fl-user-transfers.json`
(58 txs), or find one deploy via a `createDeploy`-style tx of a known deployer; then measure 7d liquidation
frequency and distinct liquidators from deploy-contract logs before the window probe.
