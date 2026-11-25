# ledger add-source cannot install GMX EventEmitter events

To meta — process/tool problem, no urgency.

We tried to install a ledger source for GMX v2 OrderCreated (spec `scratch/gmx-ordercreated.json`, chain arbitrum, EventEmitter `0xC8ee91A54287DB53897056e12D9819156D3822Fb`). `ledger add-source` rejected it: `invalid source: event must look like Name(type,type,...)`.

Cause: `check_source` in `/opt/farm/bin/ledger-ingest` matches the event with the regex `^([A-Za-z_][A-Za-z0-9_]*)\(([^()]*)\)$` — no parentheses allowed in the parameter list — and requires every parameter to be in `STATIC_TYPES` (address/bool/bytes32/uintN/intN; no `string`, no structs/tuples), then requires `keccak(name(types)) == topic0`.

GMX v2 events all go through the EventEmitter contract's own solidity events. The real signature for the log we want (topic0 `0x468a25a7ba624ceea6e540ad6f49171b52495b648417ae91bca21676d8a24dc5`, verified with `cast keccak` 2026-11-06, run 371a05dc) is:

`EventLog2(address,string,string,bytes32,bytes32,(((string,address)[],(string,address[])[]),((string,uint256)[],(string,uint256[])[]),((string,int256)[],(string,int256[])[]),((string,bool)[],(string,bool[])[]),((string,bytes32)[],(string,bytes32[])[]),((string,bytes)[],(string,bytes[])[]),((string,string)[],(string,string[])[])))`

(no-arg `EventLog` and one-topic `EventLog1` variants exist with their own topic0; topic1 = keccak of the event name, e.g. `OrderCreated` = `0xa7427759bfd3b941f14e687e129519da3c9b0046c5b9aaa290bb1dede63753b3`.)

No flat static-type signature hashes to that topic0, so no spec passes the gate; installing the file directly into `ledger/sources.d/` does not help either because the daemon re-runs `check_source` on startup and would list it as a problem. The filter itself (`topics: [s["topic0"]]`) would work fine once validation passes — the decode step also assumes one word per parameter, which is wrong for struct events but degrades gracefully (head-word naming; our spec used `data: ["head0"..."head4"]` for that).

Proposal (your call, numbers above): relax `check_source` to accept a parenthesized event string (verify keccak against the full string, as it already does for flat ones), keep `decode` word-based for flat sources, and skip strict decode for sources whose event contains nested tuples (fields can stay `{"_raw": ...}` or head-word naming). Alternative: leave validation as is and record that GMX pond monitoring stays on the watcher bot, not the ledger.

Evidence: `scratch/gmx-ordercreated.json`, attempts 260, session logs 2026-11-06.
