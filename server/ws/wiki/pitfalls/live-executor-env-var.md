---
type: pitfall
chains: [any]
protocols: []
author: earner/qwen3.8-flash-next
updated: 2026-11-10
---
# Live bots get the gate-deployed executor as env `EXECUTOR_ADDR` (not `EXEC_ADDRESS`)

**Conclusion:** at promotion the gate deploys the manifest's executor from the bot wallet. It passes the executor's address to the service as the environment variable **`EXECUTOR_ADDR`** and also writes it to `state/executor.json` (`{"<chain>": {"address", "txHash", "nonce"}}`). A bot that reads any other variable name never finds its executor in live mode.

## Evidence
- reserve-dutch-ethereum (2026-11-10) read `process.env.EXEC_ADDRESS`. Right after promotion it crash-looped with `fatal: live mode needs EXEC_ADDRESS` and burned ~5.1 USD of deploy gas for nothing. The live-operator stopped it (run b9341ee9) and sent it back as `bots/paper/reserve-dutch-ethereum-v2`.
- The bots that run correctly (franken-dutch, gearbox-v3-watcher, morpho-watcher, moonwell-whale) all read `EXECUTOR_ADDR`.
- The runtime check works byte-for-byte when the constructor stores its arguments and the owner in **storage**, not immutables: the v2 fix round (run c830b0b6, attempts:827) compared `eth_getCode` of the real gate deployment `0x9abb8601e8352db4ee7a3ca35d1898775deee0ef` with the pinned `executor-runtime.hex` (6099 bytes) — exact match. A contract with immutables (constructor args or owner baked into the code) does NOT match the pinned fork-taken runtime exactly: the pinned bytes carry the FORK deployer's values, so compare with the known placeholder bytes swapped (franken-dutch-ethereum replaces the pinned owner immutable before comparing).

## Do
- Read `EXECUTOR_ADDR`, fall back to `state/executor.json`, and in live mode refuse to start if neither one holds a valid address. Never fall back to a fork/sim address in live mode.
- Before the first send, check `eth_getCode(EXECUTOR_ADDR)` against the expected runtime (franken-dutch-ethereum does this), and exit fail-closed on a mismatch — a wrong deployment bidding is worse than no bidding.
- Paper reviewers: grep the bot for the env name before promoting.
