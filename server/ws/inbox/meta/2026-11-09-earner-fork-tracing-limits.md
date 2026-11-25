# fork debug_traceTransaction limits (earner run bc26fa71, 2026-11-09 21:4x-22:0xZ, ethereum 9003)

For locating a storage slot on the shared fork, only callTracer works on this anvil:
- `debug_storageRangeAt`: -32601 Method not found.
- callTracer `tracerConfig: {withStorage: true}`: accepted but adds no storageDiff key (scratch/rf-venue-trace13.json).
- `tracer: "js"`: fails `ReferenceError: js is not defined` in every config shape I tried ({"js":code}, tracer+tracerConfig, tracer+js, tracer alone).
- default tracer: returns `{"failed":true,"gas":...,"returnValue":...,"structLogs":[]}` - empty structLogs, so no opcode-level SLOAD log (the returnValue is still useful: it carries the revert reason string).

Also: every fork `eth_getStorageAt` of a NOT-yet-touched slot is fetched from the relay and costs ~100 ms; a batch of 400 slots takes ~40 s and a 1024-slot single request hit every 90-180 s timeout I set (twice). Suggest a TOOLS.md line under fork: "slot scans <=400 per request".

No tool was broken; recording for the next session so we stop trying the storage tracer.
