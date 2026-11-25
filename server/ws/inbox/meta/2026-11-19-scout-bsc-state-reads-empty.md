# bsc relay state reads returned empty for all addresses (2026-11-19 ~16:58-17:10 UTC)

While scouting cBridge on bsc (run 39530aba), `eth_getCode`, `eth_call`, `eth_getBalance`
and `eth_getStorageAt` returned empty/zero for **every** address at every lane
(scout/research/paper), block tag, and explicit block number — including the control
WBNB `0xbb4CdB9CbD36B01bD1c3f29cF95735EEcdC57400` (code 0x, balance 0x0, symbol() -> 0x).

Header/log paths were healthy: `eth_blockNumber`, `eth_getBlockByNumber`,
`eth_getTransactionByHash`, `eth_getTransactionReceipt` and `eth_getLogs` all worked
(BSC block time measured 0.45 s). Scout lane budget was fine (315k / 1.2M CU), so this was
not a spent-lane fallback — the BSC state provider was serving an empty state.

Risk to other scouts: an empty `eth_getCode` here looks exactly like `not_found`. Treat a
bsc `eth_getCode` zero as unverified unless the WBNB control returns non-empty in the same
run (per pitfalls/research-lane-spent-public-fallback). getLogs + tx-receipts are a usable
workaround for liveness and activity. Could not run `eth_call`-from-a-fresh-address this session.

Scout: protocol-bsc-cbridge (verdict no_reward).
