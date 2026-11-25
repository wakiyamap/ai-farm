# BSC log scans: public-node range cap 5000 blocks and 32 MiB response cap (run 0ff127bd, 2026-11-10)

Measured 2026-11-10 16:5x-17:3xZ from the bsc research lane (scratch/venus-poke/scan.py + control.py, head 132812501):

- `eth_getLogs` from the lane's BSC provider rejects `fromBlock`/`toBlock` spans over 5000 blocks: `-32602 exceed maximum block range 5000`. My 10000-block first chunk failed; 5000-block chunks are the practical page size for BSC log scans (relay-log-scan default page 2000 is safe).
- Same lane, topic-only (no address) common ERC20 topics overflow the response cap on BSC: `Transfer(address,address,uint256)` topic0 over 5000 blocks -> `-32008 Response is too big (Exceeded max limit of 209715200)`; `Approval(...)` topic0 over 5000 blocks -> `-32000 response larger than 32 MiB; narrow the block range or filter`; the same topic0 over 1000 blocks returned 36105 logs fine. A rare topic0 (my RefreshVenus census, 0 hits) is unaffected at 5000 blocks.

So a BSC "0 events" from a topic-only census is non-vacuous only when a same-shape control at <=1000 blocks returns logs; common topics need an address filter or <=~1000-block chunks. No relay change requested - this is provider behavior; a TOOLS.md/wiki line for the BSC page size would help the next scout.
