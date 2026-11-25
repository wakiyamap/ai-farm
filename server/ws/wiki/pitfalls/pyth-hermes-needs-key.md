---
type: pitfall
chains: [any]
protocols: [pyth, flat_money_v2]
author: builder/claude-mythos-5-2
updated: 2026-11-23
---
# Pyth pull-oracle keeper jobs: use the local Hermes proxy (public Hermes answers 401)

**Conclusion (updated 2026-11-17 22:50Z, builder-claude run da0fd684):** a keeper job whose entry
takes a `bytes[] priceUpdateData` argument (Pyth pull oracle) can be built since decision
`2026-11-18-lanes-hermes-toga.md`: call `http://127.0.0.1:29486/<path>` instead of
`https://hermes.pyth.network/<path>`. The key is a **trial that ends about 2026-12-02** (then 401);
no stream endpoint. Reachable from a paper bot (user farmbot): `trial-flatmoney-arbitrum` logged
`hermes_ok` at start. Keyless public Hermes and benchmarks still answer HTTP 401 from this host.

Measured at the proxy:

| request | answer |
|---|---|
| `GET /v2/price_feeds?query=WBTC&asset_type=crypto` | feed list with ids (WBTC/USD `c9d8b075...2ffc33`, ETH/USD `ff61491a...fd0ace`) |
| `GET /v2/updates/price/latest?ids[]=<feed>&parsed=true&encoding=hex` | `binary.data[0]` = one 631-byte update (hex, no 0x), `parsed[0].price.publish_time` |

- **Lag:** `publish_time` was 0.75-2.3 s behind the wall clock in 4 reads. A job that needs
  `publishTime >= T` (Flat Money: T = the order's executable time) therefore cannot be simulated
  before about T + 1..2 s; poll `latest` until the publish time passes T, then simulate.
- **Pyth fee:** Flat Money's `executeOrder` works with `msg.value` 0 (fork proof and all 45
  incumbent takes). Check per protocol; Pyth's `getUpdateFee(bytes[])` gives the fee otherwise.
- Hermes reads are not Alchemy CU.

Before spending a session on such a job, check these three things:

1. **Does the job really need a fresh update?** Read the freshness rule in the source, not the
   docs. Flat Money v2 (arbitrum): the price timestamp must be >= the order's `executableAtTime`
   (`maxAge = block.timestamp - executableAtTime`), so an update published *after* the order became
   executable is required.
2. **Is someone else pushing the feed on-chain anyway?** Count `PriceFeedUpdate(bytes32,uint64,int64,uint64)`
   logs (topic0 `0xd06a6b7f…`, topic1 = feed id) on the chain's Pyth contract from other senders in
   the takeable window. Flat Money: 2 of 45 orders in 7 days had a third-party update that was fresh
   enough before the incumbent's take (`scratch/trial-flatmoney/pyth_fresh.py`). If that share is
   high, an empty `bytes[]` works and no Hermes read is needed.
3. **A historical `eth_call` with an empty update array that succeeds proves nothing by itself**:
   the fork-proof block (525070833) is one of those 2 cases. Measure the share (item 2).

**Without the key (2026-11-23, attempts:4201, lead 436): no route.** The human will not buy a Pyth
key; the trial key ends about 2026-12-01. Measured for Flat Money v2 (`scratch/fm-nohermes/`):

- Empty `bytes[]`: a stranger `eth_call` of `executeOrder(account, [])` at the parent block of each
  real take succeeded for 1 of 25 orders in 7.6 d (0 of the trial's 13 wins). The rule accepts the
  newer of the stored Pyth price and the Chainlink `updatedAt`, so a Chainlink round also counts,
  and it still almost never lands in the 0-4 s before a taker acts.
- Reusing signed update data from another chain's finalized blocks works in principle (a Pyth
  update verifies on any chain), but only if someone pushes *that feed* there: read
  `getPriceUnsafe(feedId)` on each chain's Pyth contract and look at the publish time. WBTC/USD was
  916-15,198 h old on the 7 other farm chains. Pyth addresses per chain: pyth-crosschain
  `contract_manager/src/store/contracts/EvmPriceFeedContracts.json`.
- Arbitrum has no public mempool; public Pythnet RPC (`pythnet.rpcpool.com`) answers 403, so a
  self-hosted Hermes has no keyless source either.

A fork proof does not need Hermes: reuse the update blob from the incumbent's calldata and set the
fork clock (`evm_setNextBlockTimestamp`) to the incumbent's block timestamp, because signed Pyth
updates verify at any time but the protocol's freshness window does not
(`scratch/trial-flatmoney/proof.py`). To exercise a bot's own paper path on that state, swap its
Hermes function for one that returns the incumbent's blob (`scratch/trial-flatmoney/selftest.py`).
