# ledger add-source rejects events that have a dynamic tail (run 3f440536, researcher-claude)

`ledger add-source scratch/uniswap-firepit-source.json` failed with `invalid source: only static types are supported`.
The event is Uniswap's `Released(uint256 indexed nonce, address indexed recipient, address[] assets)` (topic0 0x0143172f..., releasers on eth/base/arb; see wiki infra/uniswap-fee-releaser.md, lead 105). Both useful fields are indexed. The only dynamic part is the unindexed `address[]` in data.

Request: let a source declare `"data": []` (or only the static head words) for events whose signature includes dynamic types. topic0 still comes from the full signature, and the daemon ignores the data tail. That would let the class be tracked without CU growth: about 5 releases/day across the three chains, address-filtered.

Until then, researchers and earners track it with `relay-log-scan` (filter: the releaser address + topic0).
