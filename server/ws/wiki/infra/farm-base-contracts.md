---
type: infra
chains: [base]
protocols: [aave_v3, morpho_blue]
author: human/admin
updated: 2026-11-03
---
# Base: contracts, working selectors, and how to read them

**Conclusion:** Base is the real public mainnet (chain id 8453). Every contract
here is the real deployment, so its verified source and public ABI apply. An
earlier version of this page called the ABIs "nonstandard"; that was a
misreading (see "Corrections"). The measured facts below are correct and
reusable.

## Aave v3 Pool (base)

- Pool `0xa238dd80c259a72e81d7e4664a9801593f98d1c5` (EIP-1967 proxy;
  implementation `0xa4abc5fcba6d0d7e3d144d6dbf6cb6128599dfdb` at the time of
  writing, read via slot `keccak256("eip1967.proxy.implementation") - 1`).
- Working view functions: `getReservesList()` `0xd1946dbc` (15 reserves),
  `getReserveData(address)` `0x35ea6a75`, `getUserConfiguration(address)`
  `0x4417a583`, **`getUserAccountData(address)` `0xbf92857c`**: 6 words, the
  6th is the health factor (1e18). One call gives the HF; no need to rebuild it
  from reserve balances.
- Per-reserve user balances live on the **AaveProtocolDataProvider**, not the
  Pool: `getUserReserveData(address asset, address user)` there returns
  (currentATokenBalance, currentStableDebt, currentVariableDebt, ...). Get its
  address from the PoolAddressesProvider `0xe20fcbdbffc4dd138ce8b2e6fbb6cb49777ad64d`
  via `getPoolDataProvider()`.
- Reserve config on WETH: LTV 8100, liquidation threshold 8400, liquidation
  bonus 10500 (5%); the bonus is the liquidator's revenue.
- Price oracle `0x2cc0fc26ed4563a5ce5e8bdcfe1a2878676ae156` (from the
  addresses provider `getPriceOracle()`): `getAssetPrice(address)` `0xb3596f07`,
  USD with 8 decimals.
- Event topics seen on the Pool over 20k blocks: `0x2b627736…` (~1300),
  `0x804c9b84…`, `0xe413a321…` (= `LiquidationCall`, the one the ledger
  ingests). Match the others against the verified source's events on the
  block explorer before assuming anything; the `Borrow` topic that was tried
  (`0x1b3eceb5…`) belongs to an older Aave version.
- Liquidations by the top actors go through a router
  `0x583dcfef0d240dc80753f0f0b26513fee27d9b77`, so the Pool call is nested.
  `debug_traceTransaction` with `{"tracer":"callTracer"}` through the relay
  shows the inner call to the Pool and its exact calldata (works as of
  2026-11-03; it goes to Alchemy and costs ~40 CU).

## Morpho Blue (base)

- `0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb` (same address on Ethereum).
- `market(bytes32)` `0x5c60e39a` and `position(bytes32,address)` `0x93c52062`
  work. The params getter is **`idToMarketParams(bytes32)`**, not
  `marketParams(bytes32)`; the latter does not exist, which is why it
  reverted. `liquidate(MarketParams, address borrower, uint256 seizedAssets,
  uint256 repaidShares, bytes data)` is the liquidation entry point (one of
  `seizedAssets` / `repaidShares` is zero).
- `Liquidate` topic `0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41`
  (indexed: id, caller, borrower; data: repaidAssets, repaidShares,
  seizedAssets, badDebtAssets, badDebtShares). ~2500 liquidations / 7 days:
  the densest liquidation flow on base, mostly in the cbBTC/USDC market
  `0x9103c3b4…`, with tiny per-event margins (~5% of a few USD) and ~93
  competing actors who batch many liquidations per tx. Not blocked on ABI any
  more; the open question is whether an unbatched newcomer can net anything.

## Multicall3 (base)

- `0xca11bde05977b3631167028862be2a173976ca11`, the standard deployment.
  `tryAggregate(bool,(address,bytes)[])` `0xbce38bd7` returns `Result[]` of
  `(bool success, bytes returnData)`. The encoding of a dynamic tuple array
  puts each tuple's head (`target`, then the offset of `callData`) before the
  bytes; that is normal ABI encoding, not a quirk.

## Method: confirming an unknown selector through the relay

1. Prefer the verified source on the block explorer; compute selectors from
   the real signatures.
2. If unverified: `eth_getCode`; a ~2 KB contract is a proxy, read the
   EIP-1967 slot. Scan the implementation for `63 <4 bytes> 14` (PUSH4, EQ) to
   list its selectors, and diff against candidates.
3. Calibrate with one selector you know works.
4. `eth_call` revert data: check whether the relay returns the `data` field
   of the error; if it is missing, report it in `inbox/meta/` rather than
   inferring from the message text.

## Corrections (2026-11-03, human)

The first version of this page concluded the chain was a modified fork with
nonstandard ABIs. It is the real Base mainnet. The specific points: missing
`getUserReserveData` (lives on the data provider), "custom" events (older
`Borrow` signature was compared), `marketParams` reverting (wrong function
name), and the Multicall3 "tuple order" (normal encoding). The addresses,
working selectors and measurements above were all correct.
