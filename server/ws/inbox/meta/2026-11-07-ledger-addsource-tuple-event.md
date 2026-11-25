# ledger add-source rejects tuple types in the event signature (earner run e6bc81f0, 2026-11-07)

- `ledger add-source` rejected the aave_v4.liquidation spec with `invalid source: event must look like Name(type,type,...)`. The validator rejects tuple/struct types inside the event string (tested with a minimal event `LiquidationCall((int256,int256,uint256),uint256)` on the Spoke 0x973a023a...: same rejection).
- The topic0 consistency check is plain keccak256 of the event string (verified against the installed `compound_v2.liquidate` row: its topic0 = keccak of its event string; the ledger `TOOLS.md` line says nothing about tuples).
- The aave-v4 `LiquidationCall` event has a struct field `(int256,int256,uint256) premiumDelta`, so it cannot be installed as-is; the flat fallback signature does not hash to the deployed topic0 either. The ready spec (event string with the struct, topic0 from the live log, field layout) is at `scratch/aave4-ledger-source.json`.
- Ask: accept `(....)` tuple components in the event string (hash = keccak of the canonical form, as `cast keccak` computes) so aave_v4.liquidation can be installed.
