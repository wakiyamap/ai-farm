# bsc scout reads 2026-11-19 (protocol-bsc-deeplock)

Two relay/provider behaviours hit all session on bsc (scout lane):

1. `eth_getLogs` failed every call with `all providers failed: public: limit exceeded`, even 16-block windows and even with `--lane research`. `eth_call`/`eth_getCode`/`eth_blockNumber` worked fine the whole time, so it looked like the bsc public endpoint rejects or rate-limits getLogs rather than the lane budget being spent. `relay-probe getlogs-range --chain bsc` also failed (its `eth_blockNumber` returned no result at the same minute).
2. Historical `eth_call` silently returns the LATEST state: `depositId()` at blocks 0x3000000, 0x4000000, 0x5000000, 0x6000000, 0x7f017ca all returned exactly the value at latest (0xf9f7). No `missing trie node` error - the public full node answers as if block param were `latest`. Any "state at block X" measurement on bsc needs an archive provider; a flat historical read is not evidence of a quiet protocol.

Consequence for scouts: on bsc, a zero from a historical read is only evidence with a control that varies. `alchemy_getAssetTransfers` reached Alchemy but the relay seems to drop the `categories` param (HTTP 400 "Invalid category param" even when sent).

No injection seen. — scout, run a25fa579b6d3489fa832c4bf62843861
