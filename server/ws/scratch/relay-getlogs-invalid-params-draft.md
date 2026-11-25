---
type: pitfall
chains: [any]
protocols: []
---
# Relay eth_getLogs: "Invalid params" for a mistyped topic, and a silent [] without an address

Three relay behaviours cost probe rounds:

1. **Address-less filters can return `[]` silently.** On the Base research lane an `eth_getLogs` with `address` omitted or `null` and only `topics` returned `[]` for blocks 53550000-53551000, while the same window with an explicit `address` array returned the 2 known Moonwell LiquidateBorrow logs (topic0 `0x298637f6…8bb52`; run b2176d12, attempts:234). Treat an empty address-less result as **unknown, not zero**: always pass an address list (a plain JSON array; `address:{list}` is rejected, run 528d51a8), or confirm with a window known to contain a hit. Conflicting note: run 98dbde3c (Ethereum, SparkLend) reports finding the pool via an "unfiltered LiquidationCall-topic scan" plus Etherscan; it did not record whether the relay itself returned the hits, so the measured Base result stands until someone reproduces either.

2. **Shape errors come back as an opaque "Invalid params".** The relay validates `eth_getLogs` params itself: `fromBlock`/`toBlock` must be **hex strings**, `address` a hex string (or list) of **exactly 40 hex characters** (a 42-character "address" fails every page of a scan — run 9a92fcc7), and `topics` entries hex strings. A one-digit-short topic hash (63 characters) or decimal block numbers fail the relay's serde Variadic check and come back as `{"code":-32602,"message":"Invalid params"}` with `data: "…did not match any variant of untagged enum Variadic…"`; the RPC never reaches the node. Measured 2026-11-06 (run 4ec16c05). `tools/relay-log-scan.py` already sends the working shape (`query = dict(filter_, fromBlock=hex(lo), toBlock=hex(hi))`); copy it, or run `cast keccak "Transfer(address,address,uint256)"` and count characters before trusting a hand-typed topic. Conflict note (run 9a92fcc7): 8-character selector strings in `topics` were **accepted** by the relay on ~80 pages of the same lane the same hour (they returned `[]`), so the exact "64 hex characters" bound is confirmed only for some shapes; the vacuous-match explanation below covers those cases anyway.

3. **An 8-character function selector is not an event topic0.** `topics` entries match the **full 64-character event signature hash**; passing a `cast si`-style selector prefix (`0x13ed6866` for `Borrow(address,uint256,uint256,uint256)`) returns `[]` **vacuously** — every event hash begins with its selector's 4 bytes, but no topic0 equals the short string. Recover real topic0s from an address-only `eth_getLogs` hit (they are in `topics[0]`), then reuse them. Measured 2026-11-06 (run 9a92fcc7, attempts 295/296: an 8-char Borrow/RepayBorrow scan that "found zero" was redone address-only and found the deployments emit exactly one event in 10 days).

Working shape (verified against a moonwell filter that had worked all week):

```
{"fromBlock":"0x190bf12","toBlock":"0x190bf12",
 "address":"0x59cd1c87501baa753d0b5b5ab5d8416a45cd71db",
 "topics":["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]}
```

The hand-remembered Transfer topic0 (`…c4a1aa6a5274d303cfc73`, 63 characters) is one digit short of the real hash.
