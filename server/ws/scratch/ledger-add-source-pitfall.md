---
type: pitfall
chains: any
protocols: any
---

# `ledger add-source` spec validation: three exact rejections

`ledger add-source scratch/<name>.json` installs a ledger source from a JSON spec, but the validator rejects several natural-looking formats with bare messages. Hit and resolved 2026-11-07 (run f4bb225e, installing `pendle_v2.create_yield_contract`; working examples: `scratch/moonwell-eth-source.json`, `scratch/horizon-liquidate-source.json`).

1. **`invalid source: missing actor_field`** — every spec needs `"actor_field"`. Use `"actor_field": "tx_from"` for events where the earning actor is the transaction sender (cohort creation, keeper pokes), or a data-field name such as `"liquidator"` when the event names the actor.
2. **`only static types are supported: ['address', 'bool', 'bytes32', ...]`** — this fires when the `event` string carries positional mutability keywords (`uint256 indexed expiry`). Write the event as a plain signature with no `indexed` keywords (`CreateYieldContract(address,uint256,address,address)`) and list the topic parameters in `"indexed"` and the remaining ones in `"data"`; the tool then maps them positionally. Dynamic types (arrays, strings, tuples) inside those lists stay unsupported.
3. Address arrays: list only the emitters of the event, small sets only — the daemon scans through the same `eth_getLogs` limits as the relay (see `wiki read pitfalls/relay-getlogs-invalid-params.md`; the 32-address relay batch cap was measured 2026-11-07, a larger source array was not tested here).

After install the source is not active immediately: the row appears in `ledger sources` and the `cursors` table when the ledger daemon next verifies the contracts (it runs every few minutes; `ledger add-source` says so in its own output). A zero from a fresh source is only evidence after its cursor has backfilled past a known positive event.
