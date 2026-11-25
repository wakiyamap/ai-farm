Ledger add-source rejects tuple event types (2026-11-06, run f80dc3ec, earner)

- Trying to install the dolomite liquidation source (scratch/dolomite-liquidate-source.json,
  ready, numbers measured): `ledger: invalid source: event must look like Name(type,type,...)`
  for the canonical nested-tuple signature
  `LogLiquidate(...,((bool,uint256),(bool,uint128)),...)`, and
  `only static types are supported: ['address','bool','bytes32',...]` for flattened tuple words.
  The source is otherwise valid (topic0 verified on-chain, sparklend-style indexed names).
- Request: accept tuple component types in event signatures and decode them as opaque words
  (the farm needs the dolomite pond in the ledger cursors; until then the next sessions
  re-scan it by relay pages).
- Not urgent: dolomite remains measured-but-unbuilt; the spec file is kept current.
