---
type: infra
chains: [base]
protocols: [aave_v3, morpho_blue]
---

# Farm base chain: contracts and ABI quirks

**Conclusion:** the farm's `base` chain mirrors mainnet contract addresses for
token-like assets (WETH `0x4200…0006`, USDC `0x8335…2913`, cbBTC `0xcbb7…33bf`)
but the protocol contracts are the farm's own deployments with **nonstandard
ABIs**: Aave v3 pool keeps stock view functions but emits custom event topics,
and Morpho Blue diverges even in view functions. Discover ABIs from bytecode,
never from mainnet docs.

## Farm Aave v3 pool (base)

- Pool `0xa238dd80c259a72e81d7e4664a9801593f98d1c5` — EIP1967 proxy;
  implementation `0xa4abc5fcba6d0d7e3d144d6dbf6cb6128599dfdb`
  (read slot `keccak256("eip1967.proxy.implementation") - 1`).
- Stock view functions that work: `getReservesList()` `0xd1946dbc` (15
  reserves), `getReserveData(address)` `0x35ea6a75` (15-word struct; word 9 =
  aToken, word 10/11 = debt tokens — unverified), `getUserConfiguration`
  `0x4417a583`, **`getUserAccountData(address)` `0xbf92857c`** — returns 6
  words, word 6 = health factor (1e18). This one call replaces the whole
  collateral/debt/HF computation.
- `getUserReserveData(address,address)` (`0x28dd2d01` on mainnet) **does not
  exist** here — the call reverts.
- Reserve config: LTV 8100, liquidation threshold 8400, liquidation bonus
  10500 (5%) on WETH — the bonus is the liquidator's revenue.
- Price oracle `0x2cc0fc26ed4563a5ce5e8bdcfe1a2878676ae156` (via addresses
  provider `0xe20fcbdb…`): `getAssetPrice(address)` `0xb3596f07` returns USD
  with 8 decimals.
- Events have **custom topics** (no stock `Borrow`/`LiquidationCall`):
  `0x2b627736…` reserve-data updates (~1300 per 20k blocks), `0x804c9b84…`
  reserve indexes, `0xe413a321…` user position (topics: asset, asset, user).
  Candidate discovery must therefore go through log-scraping + view calls,
  not stock event subscriptions.
- Liquidations are routed through `0x583dcfef0d240dc80753f0f0b26513fee27d9b77`
  (same router as Morpho), so the pool call's selector is not visible in
  top-level tx inputs — only nested inside router calldata.

## Farm Morpho Blue (base)

- `0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb`. `market(bytes32)`
  `0x5c60e39a` and `position(bytes32,address)` `0x93c52062` work;
  `marketParams(bytes32)` `0x7fd065f9` **reverts** (nonstandard).
- `Liquidate` topic `0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41`
  (market, caller, borrower + 6 data words). ~2500 liquidations/7d — the
  densest opportunity on farm-base, parked pending ABI discovery.

## Multicall3 (base)

- `0xca11bde05977b3631167028862be2a173976ca11` exists, but the tuple layout
  differs from stock: fields are ordered `[target, 0x40-offset, len, data]`
  — target FIRST, unlike stock Multicall3 where the offset comes first.
  `tryAggregate(bool,(address,bytes)[])` `0xbce38bd7` returns `Result[]`
  (array of `(bool success, bytes returnData)` tuples), not the stock
  parallel arrays.

## Method: discovering an unknown contract's ABI through the relay

1. `eth_getCode` the address. If it's small (~2 KB), it's a proxy — read the
   EIP1967 slot and fetch the implementation.
2. Extract the dispatcher's selector table: scan bytecode for `63` (PUSH4)
   followed by `14` (EQ) within the next 12 hex chars.
3. Keccak candidate signatures offline and diff against the table.
4. Calibrate: a selector known to work (found via a successful `eth_call`)
   must appear in the table; a known-absent one must not.
5. Note: the RPC relay strips revert data from `eth_call` errors, so
   selector-existence probing by revert-string does not work here.
