# 9009 elysium fork: eth_call fails "Excess blob gas not set." when the head header is relay-fetched

From 2026-11-11 ~05:30Z onward (run 44f81980, earner), every `eth_call`/`fork call` on the elysium fork (9009) returns `-32602 Excess blob gas not set.` when the fork's head header came from a relay fetch (fresh `fork reset <chain>` at head, or a reset block above the previously synced head). State-changing paths are fine (`fork fund-token`, `fork send`, `fork deploy`, `fork replay` all work, and locally mined tx blocks fix the header), so the EVM itself is healthy: only reads against the fetched-head block context fail.

Workaround used in the proof: after every `reset`/`replay`, send one cheap local tx (`fork fund-token ... 1`) before the first `eth_call` — the resulting locally mined block sets excessBlobGas and reads work until the head is re-fetched.

Please check whether the fork tool can stamp the fetched header with excessBlobGas (the chain's fetched headers carry no excessBlobGas field; anvil's hardfork shows `Bpo1`, so the EVM demands the field). Repro: `fork reset elysium 4560573` then `eth_call {to pool, data 0x1a686502} latest` -> error; `fork fund-token ... 1` then same call -> returns. scratch/elysium-lpfee3/proof3.py has the full reset->warm->read script.
